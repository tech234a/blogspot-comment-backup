import json, asyncio, aiohttp, logging
from time import perf_counter

from posts import get_blog_posts
from comments import get_comments_from_post
from util import get_url_path

starting_post = 0
posts_finished = 0
blog_posts = None
time_start = perf_counter()

downloader_count = 50
downloaders_should_pause = False
downloaders_paused = 0
downloader_tasks = []

session_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"}
session_timeout = aiohttp.ClientTimeout(total=20)
session = None

async def downloader(name, queue):

	global downloaders_should_pause
	global downloaders_paused
	global session
	global session_headers

	async def run(url):
		global starting_post
		global posts_finished
		global blog_posts
		global time_start
		global session
		try:
			comments = await get_comments_from_post(url, session, get_all_pages=True, get_replies=True, get_comment_plus_ones=True, get_reply_plus_ones=True)
			f = open(f"output/{get_url_path(url)}.json", "w")
			f.write(json.dumps(comments))
			f.close()
			total_time = perf_counter() - time_start
			print(f"{name} | [PROGRESS] post {starting_post + posts_finished + 1}/{len(blog_posts)} | total time running: {format(total_time, '.2f')}s\n")

			queue.task_done()
			posts_finished += 1
		except (asyncio.TimeoutError, TypeError):
			print(f"{name} | Request timed out")
			requeue_url(name, url)

	def requeue_url(name, url):
		print(f"{name} | requeuing post: \'{get_url_path(url)}\'")
		queue.task_done()
		queue.put_nowait(url)

	paused = False

	while not queue.empty():
		url = queue.get_nowait()
		try:
			if not downloaders_should_pause:
				if paused:
					paused = False
					downloaders_paused -= 1
					print(f"{name} | resuming from rate limit pause")
				await run(url)
			else:
				await asyncio.sleep(10)
				if not paused:
					paused = True
					downloaders_paused += 1

					if downloaders_paused == len(downloader_tasks):
						print("All downloaders paused, restarting session")
						await session.close()
						session = aiohttp.ClientSession(headers=session_headers, timeout=session_timeout)
						downloaders_should_pause = False

				requeue_url(name, url)
		except json.decoder.JSONDecodeError as e:
			try:
				print(f"{name} | paused due to rate limit")
				downloaders_should_pause = True
				# Add the url back to the queue for another task do pick up
				requeue_url(name, url)
			except Exception as e:
				queue.task_done()
				exit(e)
		except Exception as e:
			# I'm not sure how to handle errors properly while working with an async queue
			queue.task_done()
			exit(e)



async def main():
	global starting_post
	global posts_finished
	global time_start
	global blog_posts
	global session
	global session_headers
	global downloader_count

	# logging.basicConfig(format="%(message)s", level=logging.INFO)

	# blog = "https://googleblog.blogspot.com"
	# blog_posts = get_blog_posts(blog)

	# Use a file of post urls for faster debugging
	# with open("../test_data/googleblog_posts.json", "r") as file:
	with open("../test_data/blogger_googleblog.json", "r") as file:

		blog_posts = json.loads(file.read())

		posts_queue = asyncio.Queue()

		for url in blog_posts[starting_post:]:
			posts_queue.put_nowait(url)

		session = aiohttp.ClientSession(headers=session_headers, timeout=session_timeout)
		downloader_tasks = []
		for i in range(downloader_count):
			pref = "0" if i < 10 else ""
			downloader_task = asyncio.create_task(downloader(f"downloader-{pref}{i}", posts_queue))
			downloader_tasks.append(downloader_task)

		t0 = perf_counter()
		# await posts_queue.join()
		await asyncio.gather(*downloader_tasks)
		duration = perf_counter() - t0
		print("Saved %s posts in %s seconds" % (posts_finished, format(duration, '.2f')))

		await session.close()



if __name__ == '__main__':
	asyncio.run(main())