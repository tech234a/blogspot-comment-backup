import json, asyncio, aiohttp, logging, traceback
from time import perf_counter

import sys

sys.path.insert(0, './fetch/')

from fetch.posts import get_blog_posts
from fetch.comments import get_comments_from_post
from fetch.util import get_url_path

from batch_file import BatchFile

import string, random

# sharing state between downloaders is just too hard without global variables
# they will have to do for now

blog_posts = []

starting_post = 0
time_start = 0

posts_finished = 0

downloader_count = 20
downloaders_finished = 0

downloaders_should_pause = False
downloaders_paused = 0
downloader_tasks = []

restarting_session = False

session_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
session_timeout = None
session_connector = None
session = None
chars = string.ascii_letters + string.digits

log_cooldown = 0

async def downloader(name, batch_file, queue):

	global downloaders_should_pause
	global downloaders_paused
	global session
	global session_headers
	global session_connector
	global session_timeout
	global downloaders_finished
	global restarting_session

	worker_posts_downloaded = 0
	worker_posts_requeued = 0

	async def download_post(url):
		global starting_post
		global posts_finished
		global time_start
		global session
		global chars
		global log_cooldown
		try:
			comments = await get_comments_from_post(url, session, get_all_pages=True, get_replies=True, get_comment_plus_ones=True, get_reply_plus_ones=True)

			first_post = posts_finished == 0
			batch_file.add_blog_post(url, comments, first_post)

			# include a random string to prevent file name collisions
			# random_chars = "".join(random.choices(chars, k=7))
			# file_path = f"../output/{get_url_path(url)}_{random_chars}.json"
			# with open(file_path, "w") as file:
			# 	file.write(json.dumps({"url": url, "comments": comments}))

			total_time = perf_counter() - time_start
			if log_cooldown >= 20 or downloaders_should_pause or restarting_session:
				print_downloader_progress(name, batch_file.file_name, starting_post, posts_finished, blog_posts, total_time)
				print_downloader_status(name, downloaders_paused, downloaders_finished)
				log_cooldown = 0
			else:
				log_cooldown += 1
			posts_finished += 1
		except (asyncio.TimeoutError, aiohttp.client_exceptions.ClientOSError) as e:

			print(f"{name} | Retry reason: {traceback.format_exc()}")

			print(f"{name} | {batch_file.file_name} | Request timed out, requeueing in 5 seconds")
			await asyncio.sleep(5)
			requeue_url(name, url, worker_posts_requeued)

	def requeue_url(name, url, worker_posts_requeued):
		print(f"{name} | Requeuing post: \'{get_url_path(url)}\'")
		queue.append(url)
		worker_posts_requeued += 1

	def print_downloader_progress(name, batch_name, starting_post, posts_finished, blog_posts, total_time):
		print(f"{name} | [PROGRESS] {batch_file.file_name} | Post {starting_post + posts_finished + 1}/{len(blog_posts)} | Total time running: {format(total_time, '.2f')}s")

	def print_downloader_status(name, downloaders_paused, downloaders_finished):
		print(f"{name} | downloaders_paused: {downloaders_paused} downloaders_finished: {downloaders_finished}\n")

	paused = False

	while len(queue) > 0:
		if not downloaders_should_pause and (starting_post + posts_finished < len(blog_posts)):
			url = queue.pop()
			try:
				if paused:
					paused = False
					downloaders_paused -= 1
					print(f"{name} | Resuming from rate limit pause")
					print_downloader_status(name, downloaders_paused, downloaders_finished)
				await download_post(url)
				worker_posts_downloaded += 1
			except json.decoder.JSONDecodeError as e:
				try:
					print(f"{name} | Pause reason: {traceback.format_exc()}")
					print(f"{name} | Paused due to rate limit")
					print_downloader_status(name, downloaders_paused, downloaders_finished)
					if not downloaders_should_pause:
						downloaders_should_pause = True
					# Add the url back to the queue for another task do pick up
					requeue_url(name, url, worker_posts_requeued)
				except Exception as e:
					exit(e)
			except Exception as e:
				exit(e)

		else:
			await asyncio.sleep(5)
			if not paused:
				paused = True
				downloaders_paused += 1
			else:
				print(f"{name} | Waiting for all downloaders to pause")
				print_downloader_status(name, downloaders_paused, downloaders_finished)

			if not restarting_session and downloaders_should_pause and downloaders_paused >= (downloader_count - downloaders_finished):
				restarting_session = True
				# sleep for a bit so we don't resume right after hitting the captcha page
				await asyncio.sleep(10)
				print("All downloaders paused, restarting session")
				print_downloader_status(name, downloaders_paused, downloaders_finished)
				await session.close()
				session = aiohttp.ClientSession(connector=session_connector, headers=session_headers, timeout=session_timeout, connector_owner=False)
				downloaders_should_pause = False
				restarting_session = False

	downloaders_finished += 1
	print(f"{name} DONE | Posts Downloaded: {worker_posts_downloaded} | Posts Requeued: {worker_posts_requeued}")
	print_downloader_status(name, downloaders_paused, downloaders_finished)

async def download_blog(__blog_posts, __batch_file, __exclude_limit, __starting_post=0, __downloader_count=10):
	global starting_post
	global posts_finished
	global time_start
	global session
	global session_headers
	global session_connector
	global session_timeout
	global downloader_count
	global downloader_tasks
	global downloaders_finished
	global blog_posts

	starting_post = __starting_post
	downloader_count = __downloader_count

	time_start = perf_counter()

	blog_posts = __blog_posts

	posts_finished = 0
	downloaders_finished = 0
	downloaders_should_pause = False
	downloaders_paused = 0
	downloader_tasks = []

	if not session:
		session_timeout = aiohttp.ClientTimeout(total=20)
		session_connector = aiohttp.TCPConnector(limit=30)
		session = aiohttp.ClientSession(connector=session_connector, headers=session_headers, timeout=session_timeout, connector_owner=False)

	queue = []
	for post in blog_posts[starting_post:]:
		queue.append(post)

	for i in range(downloader_count):
		prefix = "0" if i < 10 else ""
		downloader_task = asyncio.create_task(downloader(f"downloader-{prefix}{i}", __batch_file, queue))
		downloader_tasks.append(downloader_task)

	t0 = perf_counter()
	# await posts_queue.join()
	await asyncio.gather(*downloader_tasks)
	duration = perf_counter() - t0
	print("Saved %s posts in %s seconds" % (posts_finished, format(duration, '.2f')))


async def main():
	global session


	# logging.basicConfig(format="%(message)s", level=logging.INFO)

	# blog = "https://googleblog.blogspot.com"
	# blog_posts = get_blog_posts(blog)

	# Use a file of post urls for faster debugging
	with open("../test_data/googleblog_posts.json", "r") as file:
		with open("../test_data/blogger_googleblog.json", "r") as file2:

			batch_file = BatchFile("../output/", 120312)
			
			# blog_posts = json.loads(file2.read())
			blog_posts_2 = json.loads(file.read())
			
			# blog_posts = ["https://0879181778.blogspot.com/2013/11/20.html"]

			batch_file.start_blog(1, "googleblog", "googleblog.blogspot.com", "a", True)
			await download_blog(blog_posts_2, batch_file, __exclude_limit=450)
			batch_file.end_blog()

			# batch_file.start_blog(1, "clean", "clean.blogspot.com", "a", False)
			# await download_blog(blog_posts_2, batch_file, __exclude_limit=450, __starting_post=3300)
			# batch_file.end_blog()

			batch_file.end_batch()

			# batch_file_2 = BatchFile("../output/", 384753)
			# blog_posts_2 = json.loads(file.read())

			# batch_file_2.start_blog(1, "buzz", "buzz.blogspot.com", "a", True)
			# await download_blog(blog_posts_2, batch_file_2, __starting_post=3300)
			# batch_file_2.end_blog()
			# batch_file_2.end_batch()

			await session.close()



if __name__ == '__main__':
	asyncio.run(main())