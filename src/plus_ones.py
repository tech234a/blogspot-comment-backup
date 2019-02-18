import requests, json

from util import remove_xssi_guard

# Gets all of the profiles who +1d a given comment
# plus_one_id - The plus_one_id of the comment
# amount - The amount of profiles to fetch
def fetch_comment_plus_ones(plus_one_id, amount, session = None):
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
    data = {"plusoneId": plus_one_id, "num": amount} 
    r = (session if session else requests).post("https://apis.google.com/wm/1/_/common/getpeople/", data=data, headers=headers)

    return r.text

def get_raw_plus_one_list(raw_response_text):
    raw_response_text = remove_xssi_guard(raw_response_text)

    obj = json.loads(raw_response_text)
    return obj[0][1]

def get_plus_ones_from_raw_response(raw_response_text):
    raw_plus_ones = get_raw_plus_one_list(raw_response_text)

    for plus_one in raw_plus_ones:
        yield get_info_from_plus_one(plus_one)

def get_info_from_plus_one(plus_one):
    results = {}

    results["user_name"] = plus_one[0] or None
    results["user_id"] = plus_one[1] or None
    results["user_profile"] = plus_one[2] or None
    results["user_avatar"] = plus_one[3] or None

    return results

def get_plus_ones_from_id(plus_one_id, amount, session = None):
    raw_response_text = fetch_comment_plus_ones(plus_one_id, amount, session)
    return get_plus_ones_from_raw_response(raw_response_text)

if __name__ == '__main__':
    plus_one_id = "4/jcsn4g3bahvbkw3padqrcvlmg5mn0h33gloaovvdj1mqmy3aj5xaowvja1pk/"

    for plus_one in get_plus_ones_from_id("4/jcsn4g3bahvbkw3padqrcvlmg5mn0h33gloaovvdj1mqmy3aj5xaowvja1pk/", 112):
        print(plus_one)

