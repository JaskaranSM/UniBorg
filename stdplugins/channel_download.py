"""
Telegram Channel Media Downloader Plugin for userbot.
usage: .geta channel_username [will  get all media from channel, tho there is limit of 3000 there to prevent API limits.]
By: @Zero_cool7870
"""
from telethon import errors
from telethon.errors.rpcerrorlist import MessageNotModifiedError, FileReferenceExpiredError
import asyncio
import os
from uniborg.util import admin_cmd, humanbytes, time_formatter
import math
import time

SLEEP_TIME = 5

def getProgressBarString(percentage):
    progress_bar_str = "[{0}{1}]\n".format(
            ''.join(["▰" for i in range(math.floor(percentage / 5))]),
            ''.join(["▱" for i in range(18 - math.floor(percentage / 5))]))
    return progress_bar_str

def getProgressString(tg_obj):
    progressStr = f"**Name:** `{tg_obj.name()}`\n" 
    progressStr += f"**CurrentFile:** `{tg_obj.currentFileName()}`\n" 
    progressStr += f"**Transferred:** `{humanbytes(tg_obj.transferredBytes())}`\n"
    progressStr += f"`{getProgressBarString(tg_obj.percent())}`"
    progressStr += f"**Percent:** `{tg_obj.percent()}%\n`"
    progressStr += f"**Speed:** `{humanbytes(tg_obj.speed())}ps`\n"
    progressStr += f"**ETA:** `{time_formatter(tg_obj.eta())}`\n"
    progressStr += f"**Total:** `{humanbytes(tg_obj.totalBytes())}`\n"
    return progressStr

async def progressSpinner(tg_obj,banner,event):
    while not tg_obj.isComplete():
        text = f"__{banner}__\n"     
        try:
            text += getProgressString(tg_obj)
        except Exception as e:
            text += str(e)
        try:
            if text != tg_obj.previous_msg_text:
                await event.edit(text)
                tg_obj.previous_msg_text = text
        except MessageNotModifiedError:
            pass
        await asyncio.sleep(SLEEP_TIME)

class TelegramDownloader:
    def __init__(self,peer_id,event):
        self.peer_id = peer_id
        self.event = event
        self._name = None
        self.current_file_name = None
        self.transferred_bytes = 0
        self.start_time = None
        self.previous_msg_text = ""
        self.file_count = 0
        self.is_complete = False
        self.last_downloaded = 0
        self.total_bytes = 0
        self.transfer_speed = 0
        self._eta = 0
        self.base_dir = None
        self.count = 0

    def speed(self):
        return self.transfer_speed

    def percent(self):
        try:
            return round(self.transferredBytes() * 100 / self.totalBytes(),2)
        except ZeroDivisionError:
            return 0.0

    def eta(self):
        return self._eta

    def totalBytes(self):
        return self.total_bytes

    def transferredBytes(self):
        return self.transferred_bytes

    def name(self):
        return self._name

    def currentFileName(self):
        return self.current_file_name

    def isComplete(self):
        return self.is_complete

    def fileCount(self):
        return self.count

    async def getMessages(self,peer_id):
        messages = []
        async for m in borg.iter_messages(peer_id,limit=None,wait_time=2):
            if m.media:
                current_file = self.getFileNameByMessage(m)
                if self.checkExists(os.path.join(self.base_dir,current_file),m.file.size):
                    continue
                messages.append(m)
        return messages


    def getSizeByMessages(self,messages):
        size = 0
        for m in messages:
            if m.media:
                size += m.file.size
                self.count += 1
        return size 

    def onTransferProgress(self,current,total):
        chunksize = current - self.last_downloaded
        self.transferred_bytes += chunksize
        self.last_downloaded = current
        diff = time.time() - self.start_time
        self.transfer_speed = self.transferredBytes() / diff
        try:
            self._eta = round((self.totalBytes() - self.transferredBytes()) / self.speed()) * 1000
        except ZeroDivisionError:
            self._eta = 0

    async def onTransferComplete(self):
        self.is_complete = True
        await self.event.edit(f"Downloaded {self.fileCount()} files in `{self.name()}`")

    def onTransferStart(self,chat):
        self.start_time = time.time()
        self._name = chat.title
        self.base_dir = chat.title + "/"
        os.makedirs(self.base_dir,exist_ok=True)

    def getFileNameByMessage(self,message):
        if message.file.name:
            return message.file.name
        elif message.file.title:
            return message.file.title
        else:
            return "file"

    def checkExists(self,file_path,size):
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) == size:
            return True
        os.remove(file_path)
        return False

    async def retryDl(self,message,timeout=1):
        logger.info(f"[RetryDownload]: {message.id} | {message.chat_id} | {timeout}")
        await asyncio.sleep(timeout)
        self.transferred_bytes = self.transferred_bytes - self.last_downloaded
        return await self.downloadMessage(message)

    async def downloadMessage(self,message):
        self.current_file_name = self.getFileNameByMessage(message)
        try:
            await borg.download_media(message,self.base_dir,progress_callback=self.onTransferProgress)
        except errors.FloodWaitError as e:
            return await self.retryDl(message,e.seconds)
        except FileReferenceExpiredError as e:
            logger.error(e)
            message = await borg.get_messages(message.chat_id,ids=message.id)
            return await self.retryDl(message)
        self.last_downloaded = 0

    async def startDownload(self):
        try:
            chat = await borg.get_entity(self.peer_id)
        except Exception as e:
            await self.onTransferComplete()
            return await self.event.edit(f"Error: {str(e)}")
        self.onTransferStart(chat)
        messages = await self.getMessages(self.peer_id)
        self.total_bytes = self.getSizeByMessages(messages)
        for message in messages:
            await self.downloadMessage(message)
        await self.onTransferComplete()


             
@borg.on(admin_cmd(pattern="geta ?(.*)", allow_sudo=True))
async def get_media(event):
    if event.fwd_from:
        return
    channel = event.pattern_match.group(1)
    try:
        channel = int(channel)
    except ValueError:
        pass
    mone = await event.reply("Downloading All Media From this Channel.")
    tgDownloader = TelegramDownloader(channel,mone)
    task1 = tgDownloader.startDownload()
    task2 = progressSpinner(tgDownloader,"DOWNLOAD PROGRESS",mone)
    await asyncio.gather(*[task1,task2])
             
             
             
