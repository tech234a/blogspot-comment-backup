import json
from time import perf_counter

from posts import get_blog_posts
from comments import get_comments_from_post
from util import get_url_path

if __name__ == '__main__':
	blog = "https://googleblog.blogspot.com"

	with open("blog_posts.json", "r") as file:
		blog_posts = json.loads(file.read())

		posts_finished = 0
		starting_post = 407

		t0 = perf_counter()
		for url in blog_posts[starting_post:]:
			comments = get_comments_from_post(url, get_all_pages=True, get_replies=False, get_comment_plus_ones=False, get_reply_plus_ones=False)
			f = open(f"output/{get_url_path(url)}.json", "w")
			f.write(json.dumps(comments))
			f.close()
			posts_finished += 1
			print(f"[PROGRESS] post {starting_post + posts_finished}/{len(blog_posts)} | total time running: {perf_counter() - t0}s\n")

		duration = perf_counter() - t0
		print("Saved %s blogs in %s seconds" % (posts_finished, duration))
    # print(json.dumps(comments[0], indent=4))

	# blog_posts = get_blog_posts(blog)
	# print(json.dumps(blog_posts))
