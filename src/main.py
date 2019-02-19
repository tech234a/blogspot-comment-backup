import json, asyncio, aiohttp, logging
from time import perf_counter

from posts import get_blog_posts
from comments import get_comments_from_post
from util import get_url_path

starting_post = 0
posts_finished = 0
blog_posts = None
time_start = perf_counter()

async def worker(name, queue, session):
	global starting_post
	global posts_finished
	global blog_posts
	global time_start

	while not queue.empty():
		try:
			url = queue.get_nowait()
			comments = await get_comments_from_post(url, session, get_all_pages=True, get_replies=True, get_comment_plus_ones=True, get_reply_plus_ones=True)
			f = open(f"output/{get_url_path(url)}.json", "w")
			f.write(json.dumps(comments))
			f.close()

			print(f"{name} | [PROGRESS] post {starting_post + posts_finished}/{len(blog_posts)} | total time running: {perf_counter() - time_start}s\n")

			queue.task_done()
			posts_finished += 1
		except Exception as e:
			# I'm not sure how to handle errors properly while working with an async queue
			queue.task_done()
			exit(e)



async def main():
	global starting_post
	global posts_finished
	global time_start
	global blog_posts

	# logging.basicConfig(format="%(message)s", level=logging.INFO)

	# blog = "https://googleblog.blogspot.com"
	# blog_posts = get_blog_posts(blog)

	# Use a file of post urls for faster debugging
	# with open("../test_data/googleblog_posts.json", "r") as file:
	with open("../test_data/blogger_googleblog.json", "r") as file:
		async with aiohttp.ClientSession() as session:

			blog_posts = json.loads(file.read())

			posts_queue = asyncio.Queue()
			worker_count = 100

			for url in blog_posts[starting_post:]:
				posts_queue.put_nowait(url)

			worker_tasks = []
			for i in range(worker_count):
				worker_task = asyncio.create_task(worker(f"worker-{i}", posts_queue, session))
				worker_tasks.append(worker_task)

			t0 = perf_counter()
			await posts_queue.join()
			duration = perf_counter() - t0
			print("Saved %s posts in %s seconds" % (posts_finished, duration))

			for task in worker_tasks:
				task.cancel()



if __name__ == '__main__':
	asyncio.run(main())