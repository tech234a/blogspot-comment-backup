import json, asyncio, aiohttp
from time import perf_counter

from posts import get_blog_posts
from comments import get_comments_from_post
from util import get_url_path

async def main():
	blog = "https://googleblog.blogspot.com"
	# blog_posts = get_blog_posts(blog)

	# Use a file of post urls for faster debugging
	with open("../test_data/blog_posts.json", "r") as file:
		async with aiohttp.ClientSession() as session:

			blog_posts = json.loads(file.read())

			posts_finished = 0
			starting_post = 407

			t0 = perf_counter()
			for url in blog_posts[starting_post:]:
				comments = await get_comments_from_post(url, session, get_all_pages=True, get_replies=False, get_comment_plus_ones=False, get_reply_plus_ones=False)
				f = open(f"output/{get_url_path(url)}.json", "w")
				f.write(json.dumps(comments))
				f.close()
				posts_finished += 1
				print(f"[PROGRESS] post {starting_post + posts_finished}/{len(blog_posts)} | total time running: {perf_counter() - t0}s\n")

			duration = perf_counter() - t0
			print("Saved %s blogs in %s seconds" % (posts_finished, duration))

if __name__ == '__main__':
	asyncio.run(main())