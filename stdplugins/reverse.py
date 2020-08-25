from uniborg.util import admin_cmd
import tracemoepy

@borg.on(admin_cmd("reverse"))
async def _(event):
    if event.fwd_from:
        return
    reply_message = await event.get_reply_message()
    if not reply_message:
        await event.edit('Reply to a gif/video/image to reverse search.')
        return
    if reply_message.video or reply_message.gif:
        file = await borg.download_media(reply_message, thumb=-1)
    else:
        file = await borg.download_media(reply_message)
    tracemoe = tracemoepy.async_trace.Async_Trace()
    search = await tracemoe.search(file, encode=True)
    result = search['docs'][0]
    msg = f"**Title**: {result['title_english']}"\
          f"\n**Similarity**: {result['similarity']*100}"\
          f"\n**Episode**: {result['episode']}"
    preview = await tracemoe.video_preview(search)
    with open('preview.mp4', 'wb') as f:
     f.write(preview)
    await event.edit(msg)
    await borg.send_file(event.chat_id, 'preview.mp4', caption = 'Match', force_document=False)
