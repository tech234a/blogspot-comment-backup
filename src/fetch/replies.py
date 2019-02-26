import json, asyncio, aiohttp
from util import remove_xssi_guard

async def fetch_comment_replies(comment_id, post_url, session):
    data = {"f.req": f'["{comment_id}",null,null,null,null,null,null,[20,null,null,1,null,null,null,1,null,"fntn",0,9,0,["{post_url}"],null,null,0],2]'}
    async with session.post("https://apis.google.com/wm/1/_/stream/getactivity/", data=data) as response:
        return await response.text()

def get_os_u_object(raw_response_text):
    raw_response_text = remove_xssi_guard(raw_response_text)

    obj = json.loads(raw_response_text)
    return obj[0][1]

def get_raw_reply_list(json_object):
    if json_object and len(json_object) >= 8:
        return json_object[7]
    else:
        return []

def get_replies_from_raw_response(raw_response_text):
    os_u_object = get_os_u_object(raw_response_text)
    raw_replies = get_raw_reply_list(os_u_object)

    for reply in raw_replies:
        yield get_info_from_reply(reply)

def get_info_from_reply(reply):
    results = {}

    results["id"] = reply[4].split("#")[1] or None
    results["date_posted"] = round(reply[3] / 1000) if reply[3] else None

    user_object = reply[25]
    results["user_name"] = user_object[0] or None
    results["user_id"] = user_object[1] or None
    results["user_avatar"] = user_object[4] or None
    results["user_profile"] = user_object[5] or None
    # disabled for now since storing gender is kinda creepy imo
    # if len(user_object) >= 7:
    #     results["user_gender"] = user_object[6] or None

    likes_object = reply[15]
    if likes_object:
        results["plus_one_id"] = likes_object[0] or None
        results["plus_one_count"] = likes_object[16] or 0

    text_object = reply[27]
    results["text"] = text_object or None

    language_object = reply[26]
    results["language_code"] = language_object[0] or None
    results["language_display"] = language_object[2] or None

    return results

async def get_replies_from_comment_id(comment_id, post_url, session):
    raw_response_text = await fetch_comment_replies(comment_id, post_url, session)
    return get_replies_from_raw_response(raw_response_text)

async def test_replies():
    # file = open("../test_data/replies_response.txt", "r", encoding="utf-8").read()
    # replies = get_replies_from_raw_response(file)
    async with aiohttp.ClientSession() as session:
        replies = await get_replies_from_comment_id("z120g3vxpu2mtn2ae04cdhjoixeixfyzjso0k", "https://blogger.googleblog.com/2019/01/an-update-on-google-and-blogger.html", session)
        for reply in replies:
            print(json.dumps(reply, indent=4, sort_keys=True))

if __name__ == '__main__':
    asyncio.run(test_replies())
