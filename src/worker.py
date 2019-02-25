import asyncio, aiohttp, json, tldextract, sys, os

from aiohttp import FormData

sys.path.insert(0, './fetch/')

from fetch.posts import get_blog_posts, MarkExclusion, NoEntries
import downloader
from batch_file import BatchFile

MASTER_SERVER = "https://blogspot-comments-master.herokuapp.com"
UPLOAD_SERVER = "http://blogstore.bot.nu"

GET_ID_ENDPOINT = f"{MASTER_SERVER}/worker/getID"
# worker id must be provided as a query parameter: id={ID}
GET_BATCH_ENDPOINT = f"{MASTER_SERVER}/worker/getBatch"
SUBMIT_EXCLUSION_BLOG_ENDPOINT = f"{MASTER_SERVER}/worker/submitExclusion"
SUBMIT_DELETED_BLOG_ENDPOINT = f"{MASTER_SERVER}/worker/submitDeleted"
SUBMIT_PRIVATE_BLOG_ENDPOINT = f"{MASTER_SERVER}/worker/submitPrivate"

UPDATE_BATCH_ENDPOINT = f"{MASTER_SERVER}/worker/updateStatus"

SUBMIT_BATCH_UNIT = f"{UPLOAD_SERVER}/submitBatchUnit"
# called by master
# VERIFY_BATCH_UNIT = f"{UPLOAD_SERVER}/getVerifyBatchUnit"

WORKER_VERSION = 1
WORKER_BATCH_SIZE = 500

# Stop trying to connect to master after 18 hours
MASTER_SLEEP_TOTAL = (60 * 60) * 18
# MASTER_SLEEP_TOTAL = 10
# Multiply the sleep amount each retry
# MASTER_SLEEP_INCREMENT = 5
MASTER_SLEEP_INCREMENT = 30
# Stop multiplying after 180 seconds
# MASTER_SLEEP_MAXIMUM = 10
MASTER_SLEEP_MAXIMUM = 180

async def get_worker_id(session):

    def fail_func(response_status):
        print(f"[get_worker_id] The server response was unsuccessful ({response_status}), unable to get a worker ID")

    response = await retry_request_on_fail(session.get, fail_func, True, False, GET_ID_ENDPOINT)
    if response and response.status == 200:
        text = await response.text()
        return text

async def get_batch(worker_id, session):

    def fail_func(response_status):
        print(f"[get_batch] The server response was unsuccessful ({response_status}), unable to get a batch")

    params = {"id": worker_id}
    response = await retry_request_on_fail(session.get, fail_func, True, True, GET_BATCH_ENDPOINT, params=params)
    if response and response.status == 200:
        text = await response.text()
        obj = json.loads(text)
        return {
            "batch_id": obj["batchID"], 
            "random_key": obj["randomKey"], 
            "file_offset": obj["offset"], 
            "exclusion_limit": obj["limit"],
            "batch_type": obj["assignmentType"],
            "content": obj["content"]
        }

async def update_batch_status(worker_id, batch_id, random_key, status, session):
    def fail_func(response_status):
        print(f"[update_batch_status] The server response was unsuccessful ({response_status}), unable to update batch status")

    params = {
        "id": worker_id, 
        "batchID": batch_id, 
        "randomKey": random_key,
        "status": status
    }
    response = await retry_request_on_fail(session.get, fail_func, True, False, UPDATE_BATCH_ENDPOINT, params=params)
    if response and response.status == 200:
        print(f"Successfully updated batch status: worker_id: {worker_id} | batch_id: {batch_id}")
        return True


async def submit_batch_exception(exception_type, endpoint, worker_id, batch_id, random_key, blog_name, session):

    variables_string = f"worker_id: {worker_id} batch_id: {batch_id} random_key: {random_key} blog_name: {blog_name}"

    def fail_func(response_status):
        print(f"[submit_batch_exception] The server response was unsuccessful ({response_status}), unable to submit as {exception_type}\n{variables_string}")

    params = {
        "id": worker_id, 
        "batchID": batch_id, 
        "randomKey": random_key
    }
    params[exception_type] = blog_name
    response = await retry_request_on_fail(session.get, fail_func, True, False, endpoint, params=params)

    if response and response.status == 200:
        text = await response.text()
        success = text == "Success"
        if success:
            print(f"Submitted batch for {exception_type}\n{variables_string}")
            return True
        else:
            print(f"Failed to submit {exception_type}\n{variables_string}")
            return False

async def submit_exclusion(worker_id, batch_id, random_key, blog_name, session):
    success = await submit_batch_exception("exclusion", SUBMIT_EXCLUSION_BLOG_ENDPOINT, worker_id, batch_id, random_key, blog_name, session)
    return success

async def submit_private(worker_id, batch_id, random_key, blog_name, session):
    success = await submit_batch_exception("private", SUBMIT_PRIVATE_BLOG_ENDPOINT, worker_id, batch_id, random_key, blog_name, session)
    return success

async def submit_deleted(worker_id, batch_id, random_key, blog_name, session):
    success = await submit_batch_exception("deleted", SUBMIT_DELETED_BLOG_ENDPOINT, worker_id, batch_id, random_key, blog_name, session)
    return success

async def upload_batch(worker_id, batch_id, random_key, version, file_path, file_name, session):

    def fail_func(response_status):
        print(f"[upload_batch] The server response was unsuccessful ({response_status}), unable to upload batch")

    async def create_request(url):
        data = FormData()
        data.add_field("workerID", str(worker_id))
        data.add_field("batchID", str(batch_id))
        data.add_field("batchKey", str(random_key))
        data.add_field("version", str(version))
        data.add_field("data", open(file_path, "rb"), filename=file_name, content_type="application/x-gzip")
        response = await session.post(url, data=data)
        return response

    url = SUBMIT_BATCH_UNIT

    # response = await retry_request_on_fail(create_request, fail_func, False, False, url)
    response = await create_request(url)
    if response.status == 200:
        print(f"Successfully uploaded batch: worker_id: {worker_id} batch_id: {batch_id} | file_path: {file_path}")
        return True
    else:
        print(f"Unable to upload batch: worker_id: {worker_id} batch_id: {batch_id} | file_path: {file_path}")
        return False

async def download_batch(worker_id, batch_id, batch_type, batch_content, random_key, batch_size, offset, domains, exclusion_limit, session):

    domains.seek(offset)

    file_path = "../output/"
    batch_file = BatchFile(file_path, batch_id)

    async def download_blog(blog_name, first_blog):
        try:
            print(f"Downloading blog: {blog_name}")
            blog_posts = await get_blog_posts(f"https://{blog_name}.blogspot.com", exclusion_limit, session)
            # The blog cannot be found / is deleted
            if blog_posts == "nf":
                print(f"Marking as deleted: batch_id: {batch_id} | blog_name: {blog_name}")
                await submit_deleted(worker_id, batch_id, random_key, blog_name, session)
                blog_domain = f"{blog_name}.blogspot.com"
                batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "d", first_blog)
                batch_file.end_blog()
            # The blog is private
            elif blog_posts == "pr":
                print(f"Marking as private: batch_id: {batch_id} | blog_name: {blog_name}")
                await submit_private(worker_id, batch_id, random_key, blog_name, session)
                blog_domain = f"{blog_name}.blogspot.com"
                batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "p", first_blog)
                batch_file.end_blog()
            # Other errors
            elif blog_posts == "oe":
                print(f"Marking as exclusion: batch_id: {batch_id} | blog_name: {blog_name}")
                await submit_exclusion(worker_id, batch_id, random_key, blog_name, session)
                blog_domain = f"{blog_name}.blogspot.com"
                batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "e", first_blog)
                batch_file.end_blog()
            else:
                blog_tld = tldextract.extract(blog_posts[0])
                blog_domain = f"{blog_tld.subdomain}.{blog_tld.domain}.{blog_tld.suffix}"

                batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "a", first_blog)
                await downloader.download_blog(blog_posts, batch_file, exclusion_limit)
                batch_file.end_blog()

        except MarkExclusion:
            print(f"Marking as exclusion: batch_id: {batch_id} | blog_name: {blog_name}")
            await submit_exclusion(worker_id, batch_id, random_key, blog_name, session)
            blog_domain = f"{blog_name}.blogspot.com"
            batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "e", first_blog)
            batch_file.end_blog()
        except NoEntries:
            print(f"Blog has no posts: batch_id: {batch_id} | blog_name: {blog_name}")
            blog_domain = f"{blog_name}.blogspot.com"
            batch_file.start_blog(WORKER_VERSION, blog_name, blog_domain, "a", first_blog)
            batch_file.end_blog()


    if batch_type == "list":
        # batch_size = 5
        print("Downloading multiple domains (list)")
        for i in range(batch_size):
            print(f"[BATCH PROGRESS] {i}/{batch_size}")
            blog_name = domains.readline().replace("\n", "")
            if blog_name != "":
                first_blog = (i == 0)
                await download_blog(blog_name, first_blog)
            else:
                print("Reached end of domains list")

    elif batch_type == "domain":
        if batch_content != "":
            print(f"Downloading single domain: {batch_content}")
            await download_blog(batch_content, True)
        else:
            raise Exception(f"Invalid batch_content: {batch_content}")
    else:
        raise Exception("Invalid batch_type")

    batch_file.end_batch()

    file_path = batch_file.directory + batch_file.file_name
    file_name = batch_file.file_name

    upload_response = await upload_batch(worker_id, batch_id, random_key, WORKER_VERSION, file_path, file_name, session)
    await update_batch_status(worker_id, batch_id, random_key, "c" if upload_response else "f", session)
    print(f"Deleting batch file | file_path: {file_path} | status: {upload_response}")
    os.remove(file_path)

async def retry_request_on_fail(func, fail_func, check_text, check_batch_fail=False, *args, **kwargs):

    total_slept = 0
    sleep_amount = MASTER_SLEEP_INCREMENT

    while total_slept < MASTER_SLEEP_TOTAL:
        try:
            response = await func(*args, **kwargs)
            if check_batch_fail:
                text = await response.text()
                obj = json.loads(text)
                if "batchID" in obj and obj["batchID"] != "Fail":
                    return response
                else:
                    fail_func(response.status)
                    print(f"Retrying request | sleep_amount: {sleep_amount} total_slept: {total_slept}")
                    await asyncio.sleep(sleep_amount)
                    total_slept += sleep_amount
                    if sleep_amount < MASTER_SLEEP_MAXIMUM:
                        sleep_amount += MASTER_SLEEP_INCREMENT
            elif check_text:
                text = await(response.text())
                print(text)
                if text != "Fail" and response.status == 200:
                    # print("Success!")
                    return response
                else:
                    fail_func(response.status)
                    print(f"Retrying request | sleep_amount: {sleep_amount} total_slept: {total_slept}")
                    await asyncio.sleep(sleep_amount)
                    total_slept += sleep_amount
                    if sleep_amount < MASTER_SLEEP_MAXIMUM:
                        sleep_amount += MASTER_SLEEP_INCREMENT

            elif response.status == 200:
                print("Success!")
                return response
            else:
                fail_func(response.status)
                print(f"Retrying request | sleep_amount: {sleep_amount} total_slept: {total_slept}")
                await asyncio.sleep(sleep_amount)
                total_slept += sleep_amount
                if sleep_amount < MASTER_SLEEP_MAXIMUM:
                    sleep_amount += MASTER_SLEEP_INCREMENT
        except asyncio.TimeoutError:
            fail_func()
            print(f"Retrying request | sleep_amount: {sleep_amount} total_slept: {total_slept}")
            await asyncio.sleep(sleep_amount)
            total_slept += sleep_amount
            if sleep_amount < MASTER_SLEEP_MAXIMUM:
                sleep_amount += MASTER_SLEEP_INCREMENT


    print(f"Request retry reached max ({MASTER_SLEEP_TOTAL} seconds)")
    sys.exit(1)
    # return False


async def main():

    with open("../domains.txt", "r") as domains:
        async with aiohttp.ClientSession() as session:
            print("Requesting worker ID")
            worker_id = await get_worker_id(session)
            # worker_id = "27747438-9825-51e1-9578-8807297944e6"
            if worker_id:
                print(f"Received worker ID: {worker_id}")
                while True:
                    print("Requesting new batch...")
                    batch = await get_batch(worker_id, session)
                    print(f"Received batch: {batch}")
                    if batch:
                        batch_id = batch["batch_id"]
                        batch_type = batch["batch_type"]
                        random_key = batch["random_key"]
                        batch_content = batch["content"]
                        offset = int(batch["file_offset"])
                        exclusion_limit = int(batch["exclusion_limit"])

                        await download_batch(worker_id, batch_id, batch_type, batch_content, random_key, WORKER_BATCH_SIZE, offset, domains, exclusion_limit, session)
                    else:
                        print("Unable to get batch")

                    await asyncio.sleep(10)

    if downloader.session:
        await downloader.session.close()

async def download_domains():
    async with aiohttp.ClientSession() as session:

        def fail_func():
            print(f"Failed to get domains.txt, retrying")

        domains_response = await retry_request_on_fail(session.get, fail_func, False, False, "https://blogspot-comments-master.herokuapp.com/worker/domains.txt")

        with open("../domains.txt", "wb") as domains:
            while True:
                # download in chunks of 10MB
                chunk = await domains_response.content.read((1000 * 1000) * 10)
                if not chunk:
                    break
                domains.write(chunk)

if __name__ == '__main__':

    # create the output folder for the gzipped batches
    if not os.path.isdir("../output"):
        os.makedirs("../output")

    # download the domains list
    if not os.path.exists("../domains.txt"):
        print("Downloading domains list..")
        asyncio.run(download_domains())

    asyncio.run(main())