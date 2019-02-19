import re, json, logging
import asyncio, aiohttp

from time import sleep, perf_counter

from util import get_bracket_pairs, remove_xssi_guard, get_url_path
from replies import get_replies_from_comment_id
from plus_ones import get_plus_ones_from_id

blogger_object_pattern = re.compile(r'data:(\["os\.blogger",[\s\S]*?)}\);</script>')

def extract_blogger_object_from_html(html):
    os_blogger = blogger_object_pattern.search(html)[1]
    parsed = json.loads(os_blogger)

    return parsed

def extract_continuation_key(blogger_object):
    continuation_key = blogger_object[1][1]
    return continuation_key

def get_total_comment_count(initial_blogger_object):
    return initial_blogger_object[2][0]

# parsing os blogger comments

def get_raw_comment_list(blogger_object):
    return blogger_object[1][7]

def get_comments_from_blogger_object(blogger_object):
    comment_list = get_raw_comment_list(blogger_object)
    for i, comment in enumerate(comment_list):
        comment_list[i] = get_info_from_comment(comment)

    return comment_list

def get_info_from_comment(comment, return_info_list=False):
    comment_type = comment[5][0]

    if not comment_type in [1001, 3]:
        raise ValueError(f"Unknown comment_type: \'{comment_type}\'")

    comment_id = comment[5][1]

    comment_info_dict = comment[6]
    comment_info_key = next(iter(comment_info_dict))

    info_list = comment_info_dict[comment_info_key]
    results = {}

    results["id"] = comment_id or None
    results["type"] = comment_type or None
    
    results["reply_count"] = info_list[93] or 0

    results["date_posted"] = info_list[5] or None
    results["domain"] = info_list[2] or None

    user_object = info_list[136]
    results["user_name"] = user_object[0] or None
    results["user_id"] = user_object[1] or None
    results["user_avatar"] = user_object[4] or None
    results["user_profile"] = user_object[5] or None
    # disabled for now since storing gender is kinda creepy imo
    # if len(user_object) >= 7:
    #     results["user_gender"] = user_object[6] or None
    
    likes_object = info_list[73]
    if likes_object:
        results["plus_one_id"] = likes_object[0] or None
        results["plus_one_count"] = likes_object[16] or 0
    
    results["text"] = info_list[137] if info_list[137] else None

    language_object = info_list[141]
    if len(language_object) == 3: 
        results["language_code"] = language_object[0] or None
        results["language_display"] = language_object[2] or None

    results["share_string"] = info_list[10] or None

    if return_info_list:
        return (results, info_list)
    else:
        return results  

async def fetch_initial_page(post_url, session):
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
    params = {"first_party_property": "BLOGGER", "query": post_url}
    async with session.get("https://apis.google.com/u/0/_/widget/render/comments", params=params, headers=headers) as response:
        text = await response.text()
        return (text, response.status)

async def fetch_more_comments(continuation_key, post_url, session):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
    data = {"f.req": f'[[null,[[null,null,null,null,2]],[1,[20,\"{continuation_key}\"],null,[[[2,[null,\"\"]]]],true],[100]],[[\"{post_url}\",null,null,null,0,null,\"{post_url}\",null,null,1,[20,null,null,1,null,null,null,1,null,\"fntn\",0,9,0,[\"{post_url}\"],null,null,0],null,null,null,null,1,null,null,null,null,0,null,null,3,1,\"ADSJ_i2qch7-NelDrYpMAgUEL3IyfvpRaOpIlNdE_bvIQ75NJOZBrBOcjySzgO6TLTwV505qclfGXYIJhMfE5caBt_gnFo0oJQMYepGtofNznk9sXjdUpWpbuvR9fVGZg5UE5s63b2jaYidM-u0YJobnkro9YS07tqwxEfgTeBOKzWrTTOVchhsesdkGf_5Bt2nIVwQX-CBt0dMjHSlQOVRDK8lDWMDDmByx31C9iLDhEhuG6dr0IdYCDriTB8orFKbx4AJztSfIqaJgpDhjauRnxyGTfIeDCF615Dhc5oQRNWv5DC3lk0Tdz76D42zH768dAYF1_pyJLZX8CdvH9V2MlBc6bvnCJdZWmHaWi1U17imK\",20,null,null,[null,null,0,0,0],1,0,null,0],\"{post_url}\",\"{post_url}\",[20,null,null,1,null,null,null,1,null,\"fntn\",0,9,0,[\"{post_url}\"],null,null,0],0,\"\"]]'}
    
    async with session.post("https://apis.google.com/wm/1/_/sw/bs", data=data, headers=headers) as response:
        text = await response.text()

        response_string = remove_xssi_guard(text)
        blogger_object = json.loads(response_string)[0]

        return {"comments": get_comments_from_blogger_object(blogger_object), "continuation_key": extract_continuation_key(blogger_object)}

async def process_comments(comments, session, post_url=None, get_replies=False, get_comment_plus_ones=False, get_reply_plus_ones=False):
    # There's probably a way to avoid creating two loops here
    # but I'm not experienced enough with asyncio to figure it out

    reply_tasks = {}
    plus_one_tasks = {}
    reply_plus_one_tasks = {}

    # Initial loop to start all of the tasks in parallel
    for comment in comments:
        if get_replies and comment["reply_count"] > 0:
            # This probably isn't the python way of doing async, but it works fine for now
            reply_task = asyncio.create_task(get_replies_from_comment_id(comment["id"], post_url, session))
            reply_task.comment = comment
            reply_tasks[comment["id"]] = reply_task

        if get_comment_plus_ones and comment["plus_one_id"] and comment["plus_one_count"] > 0:
            plus_one_task = asyncio.create_task(get_plus_ones_from_id(comment["plus_one_id"], comment["plus_one_count"], session))
            plus_one_task.comment = comment
            plus_one_tasks[comment["id"]] = plus_one_task

    if get_replies:
        await asyncio.gather(*list(reply_tasks.values()), return_exceptions=True)
        # Loop to assign the replies to their respective comments
        if get_reply_plus_ones:
            for key, value in reply_tasks.items():
                replies = list(value.result())
                value.comment["replies"] = replies
                if get_reply_plus_ones:
                    for reply in replies:
                        if reply["plus_one_id"] and reply["plus_one_count"] > 0:
                            reply_plus_one_task = asyncio.create_task(get_plus_ones_from_id(reply["plus_one_id"], reply["plus_one_count"], session))
                            reply_plus_one_task.reply = reply
                            reply_plus_one_tasks[reply["id"]] = reply_plus_one_task
        else:
            for key, value in reply_tasks.items():
                value.comment["replies"] = list(value.result())
    
    if get_comment_plus_ones:
        await asyncio.gather(*list(plus_one_tasks.values()), return_exceptions=True)

        for key, value in plus_one_tasks.items():
            value.comment["plus_ones"] = list(value.result())

    if get_reply_plus_ones:
        await asyncio.gather(*list(reply_plus_one_tasks.values()), return_exceptions=True)
        for key, value in reply_plus_one_tasks.items():
            value.reply["plus_ones"] = list(value.result())

# Retrieves comments and replies
# get_all_pages 
#   - Use the continuation key to get all pages of comments (20 comments per page) 
#   - The amount of additional network requests is (amount of comments / 20) (excluding replies)
# get_replies 
#   - Retrieve all of the replies for each comment
#   - An additional network request is made for each comment that has >1 replies
# get_plus_one_list 
#   - Retrieve a list of all the authors that +1'd each comment
#   - An additional network request is made for each comment and reply that has >1 plus_ones
# session - To reuse an existing aiohttp.ClientSession object (performance improvement)
async def get_comments_from_post(post_url, session, get_all_pages=True, get_replies=False, get_comment_plus_ones=False, get_reply_plus_ones=False):

    results = []
    page = 1
    logging.info(f"- Getting comments for: {post_url}")

    fetch_response = await fetch_initial_page(post_url, session)
    logging.info(f"  Received HTML | status: {fetch_response[1]}")

    blogger_object = extract_blogger_object_from_html(fetch_response[0])
    comments = get_comments_from_blogger_object(blogger_object)

    logging.info("  Total comments: %s" % get_total_comment_count(blogger_object))
    logging.info("  Extracting comments")
    logging.info("    page 1 (%s)" % len(comments))

    # Add the comments from the initial html (first 20)
    await process_comments(comments, session, post_url, get_replies, get_comment_plus_ones, get_reply_plus_ones)
    results.extend(comments)

    if get_all_pages:
        continuation_key = extract_continuation_key(blogger_object)
        while True:
            page += 1
            next_comments = await fetch_more_comments(continuation_key, post_url, session)

            continuation_key = next_comments["continuation_key"]
            comments = next_comments["comments"]

            if not len(comments) or not continuation_key: break

            logging.info("    page %s (%s)" % (page, len(comments)))
            await process_comments(comments, session, post_url, get_replies, get_comment_plus_ones, get_reply_plus_ones)
            results.extend(comments)
    logging.info("  Finished")
    return results


async def test_urls():
    test_urls = [
        # "https://raazwebcity.blogspot.com/2018/05/twitter-to-discontinued.html",
        # "http://raazwebcity.blogspot.com/2018/09/best-wordpress-seo-tips.html",
        # "https://blogger-developers.googleblog.com/2011/11/introducing-custom-mobile-templates.html",
        # "https://blogger-developers.googleblog.com/2013/04/improvements-to-blogger-template-html.html",
        "https://blogger.googleblog.com/2019/01/an-update-on-google-and-blogger.html"
    ]

    async with aiohttp.ClientSession() as session:
        # print(await fetch_initial_page(test_urls[0], session))
        # 
        
        runs = 3
        
        total_elapsed = 0
        for i in range(runs):
            t0 = perf_counter()
            comments = await get_comments_from_post(test_urls[0], session, get_all_pages=False, get_replies=True, get_comment_plus_ones=True, get_reply_plus_ones=True)
            t1 = perf_counter() - t0
            total_elapsed += t1
        print("Took %f seconds with average %f\n\n\n\n\n" % (total_elapsed, total_elapsed / runs))
        print(json.dumps(comments[0], indent=4))

if __name__ == '__main__':
    asyncio.run(test_urls())
