from ..scrapetube import get_json_from_html, type_property_map, search_dict, get_next_data, get_videos_items, get_page_context

import orjson
import httpx
import asyncio
from typing import AsyncGenerator, Optional
from typing_extensions import Literal

__all__ = [
    "get_session",
    "get_initial_data",
    "get_ajax_data",
    "get_video",
    "get_videos",
    "get_channel",
    "get_playlist",
]

# YouTube 先前更新了 shorts 的 JSON tree，但 pypi 上的 scrapetube 一直沒有更新
# https://github.com/dermasmid/scrapetube/issues/65
type_property_map['shorts'] = 'reelWatchEndpoint'

def get_session() -> httpx.AsyncClient:
    session = httpx.AsyncClient()
    session.headers[
        "User-Agent"
    ] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    session.headers["Accept-Language"] = "en"
    return session

async def get_initial_data(session: httpx.AsyncClient, url: str) -> str:
    session.cookies.set("CONSENT", "YES+cb", domain=".youtube.com")
    response = await session.get(url, params={"ucbcb":1})

    html = response.text
    return html

async def get_ajax_data(
    session: httpx.AsyncClient,
    api_endpoint: str,
    api_key: str,
    next_data: dict,
    client: dict,
) -> dict:
    data = {
        "context": {"clickTracking": next_data["click_params"], "client": client},
        "continuation": next_data["token"],
    }
    response = await session.post(api_endpoint, params={"key": api_key}, json=data)
    return response.json()

async def get_video(
    id: str,
) -> dict:
    """Get a single video.

    Parameters:
        id (``str``):
            The video id from the video you want to get.
    """

    try:
        session = get_session()
        url = f"https://www.youtube.com/watch?v={id}"
        html = await get_initial_data(session, url)
        client = orjson.loads(
            get_json_from_html(html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}'
        )["client"]
        session.headers["X-YouTube-Client-Name"] = "1"
        session.headers["X-YouTube-Client-Version"] = client["clientVersion"]
        data = orjson.loads(
            get_json_from_html(html, "var ytInitialData = ", 0, "};") + "}"
        )
        return next(search_dict(data, "videoPrimaryInfoRenderer"))
    finally:
        await session.aclose()

async def get_videos(
    url: str, api_endpoint: str, selector: str, limit: int, sleep: int, sort_by: Optional[str] = None
) -> AsyncGenerator[dict, None]:
    try:
        session = get_session()
        is_first = True
        quit_it = False
        count = 0
        page_context = None
        while True:
            if is_first:
                html = await get_initial_data(session, url)
                client = orjson.loads(
                    get_json_from_html(html, "INNERTUBE_CONTEXT", 2, '"}},') + '"}}'
                )["client"]
                api_key = get_json_from_html(html, "innertubeApiKey", 3)
                session.headers["X-YouTube-Client-Name"] = "1"
                session.headers["X-YouTube-Client-Version"] = client["clientVersion"]
                data = orjson.loads(
                    get_json_from_html(html, "var ytInitialData = ", 0, "};") + "}"
                )
                page_context = get_page_context(data)
                next_data = get_next_data(data, sort_by)
                is_first = False
                if sort_by and sort_by != "newest": 
                    continue
            else:
                data = await get_ajax_data(session, api_endpoint, api_key, next_data, client)
                next_data = get_next_data(data)
            for result in get_videos_items(data, selector, page_context):
                try:
                    count += 1
                    yield result
                    if count == limit:
                        quit_it = True
                        break
                except GeneratorExit:
                    quit_it = True
                    break

            if not next_data or quit_it:
                break

            await asyncio.sleep(sleep)
    finally:
        await session.aclose()

async def get_channel(channel_id: str = None,
    channel_url: str = None,
    channel_username: str = None,
    limit: int = None,
    sleep: int = 1,
    sort_by: Literal["newest", "oldest", "popular"] = "newest",
    content_type: Literal["videos", "shorts", "streams"] = "videos",
) -> AsyncGenerator[dict, None]:
    """Get videos for a channel.

    Parameters:
        channel_id (``str``, *optional*):
            The channel id from the channel you want to get the videos for.
            If you prefer to use the channel url instead, see ``channel_url`` below.

        channel_url (``str``, *optional*):
            The url to the channel you want to get the videos for.
            Since there is a few type's of channel url's, you can use the one you want
            by passing it here instead of using ``channel_id``.

        channel_username (``str``, *optional*):
            The username from the channel you want to get the videos for.
            Ex. ``LinusTechTips`` (without the @).
            If you prefer to use the channel url instead, see ``channel_url`` above.

        limit (``int``, *optional*):
            Limit the number of videos you want to get.

        sleep (``int``, *optional*):
            Seconds to sleep between API calls to youtube, in order to prevent getting blocked.
            Defaults to 1.

        proxies (``dict``, *optional*):
            A dictionary with the proxies you want to use. Ex:
            ``{'https': 'http://username:password@101.102.103.104:3128'}``
        
        sort_by (``str``, *optional*):
            In what order to retrieve to videos. Pass one of the following values.
            ``"newest"``: Get the new videos first.
            ``"oldest"``: Get the old videos first.
            ``"popular"``: Get the popular videos first. Defaults to "newest".

        content_type (``str``, *optional*):
            In order to get content type. Pass one of the following values.
            ``"videos"``: Videos
            ``"shorts"``: Shorts
            ``"streams"``: Streams
    """

    base_url = ""
    if channel_url:
        base_url = channel_url
    elif channel_id:
        base_url = f"https://www.youtube.com/channel/{channel_id}"
    elif channel_username:
        base_url = f"https://www.youtube.com/@{channel_username}"

    url = "{base_url}/{content_type}?view=0&flow=grid".format(
        base_url=base_url,
        content_type=content_type,
    )
    api_endpoint = "https://www.youtube.com/youtubei/v1/browse"
    videos = get_videos(url, api_endpoint, type_property_map[content_type], limit, sleep, sort_by)
    async for video in videos:
        yield video

async def get_playlist(
    playlist_id: str, limit: Optional[int] = None, sleep: int = 1
) -> AsyncGenerator[dict, None]:
    """Get videos for a playlist.

    Parameters:
        playlist_id (``str``):
            The playlist id from the playlist you want to get the videos for.

        limit (``int``, *optional*):
            Limit the number of videos you want to get.

        sleep (``int``, *optional*):
            Seconds to sleep between API calls to youtube, in order to prevent getting blocked.
            Defaults to 1.
    """

    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    api_endpoint = "https://www.youtube.com/youtubei/v1/browse"
    videos = get_videos(url, api_endpoint, "playlistVideoRenderer", limit, sleep)
    async for video in videos:
        yield video