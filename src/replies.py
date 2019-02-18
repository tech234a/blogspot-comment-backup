import json, requests
from util import remove_xssi_guard

def fetch_comment_replies(comment_id, post_url, session = None):
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
    data = {"f.req": f'["{comment_id}",null,null,null,null,null,null,[20,null,null,1,null,null,null,1,null,"fntn",0,9,0,["{post_url}"],null,null,0],2]'}
    r = (session if session else requests).post("https://apis.google.com/wm/1/_/stream/getactivity/", data=data, headers=headers)

    return r.text

def get_os_u_object(raw_response_text):
    raw_response_text = remove_xssi_guard(raw_response_text)

    obj = json.loads(raw_response_text)
    return obj[0][1]

def get_raw_replies_list(json_object):
    return json_object[7]

def get_replies_from_raw_response(raw_response_text):
    os_u_object = get_os_u_object(raw_response_text)
    raw_replies = get_raw_replies_list(os_u_object)

    replies = []
    for reply in raw_replies:
        replies.append(get_info_from_reply(reply))
    return replies

def get_replies_from_comment_id(comment_id, post_url, session = None):
    raw_response_text = fetch_comment_replies(comment_id, post_url, session)
    return get_replies_from_raw_response(raw_response_text)

def get_info_from_reply(reply):
    results = {}

    results["id"] = reply[4].split("#")[1] or None
    results["date_posted"] = reply[3] or None

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
        likes = likes_object[16] or 0
        results["plus_ones"] = likes

    text_object = reply[27]
    results["text"] = text_object or None

    language_object = reply[26]
    results["language_code"] = language_object[0] or None
    results["language_display"] = language_object[2] or None

    return results

if __name__ == '__main__':

    # file = open("../test_data/replies_response.txt", "r", encoding="utf-8").read()
    # replies = get_replies_from_raw_response(file)
    
    replies = get_replies_from_comment_id("z120g3vxpu2mtn2ae04cdhjoixeixfyzjso0k", "https://blogger.googleblog.com/2019/01/an-update-on-google-and-blogger.html")
    for reply in replies:
        print(json.dumps(reply, indent=4, sort_keys=True))