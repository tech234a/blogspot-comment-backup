import time, json, gzip

class BatchError(Exception):
	pass


class BatchFile:
	def __init__(self, directory, batch_id):
		self.batch_id = batch_id
		self.directory = directory
		self.file_name = f"{self.batch_id}.json.gz"
		self.batch_file = gzip.open(f"{self.directory}{self.file_name}", "w")
		self.batch_file.write(b"[")

		self.closed = False

		self.blog_started = False

	def end_batch(self):
		self.batch_file.write(b"\n]")
		self.batch_file.close()

	def start_blog(self, version, blog_name, domain, first_blog=False):
		if not self.blog_started:
			self.blog_started = True
			blog_header_obj = {
				"version": 1,
				"fetch_date": round(time.time()),
				"blog_name": blog_name,
				"domain": domain,
				"posts": []
			}
			comma = "," if not first_blog else ""
			blog_header = f"{comma}\n    " + json.dumps(blog_header_obj)[:-2] + "\n"
			self.batch_file.write(blog_header.encode("utf-8"))
		else:
			raise BatchError("Cannot start blog: there is already a blog started")

	def end_blog(self):
		if self.blog_started:
			end_text = b"\n    ]}"
			self.batch_file.write(end_text)
			self.blog_started = False
		else:
			raise BatchError("Cannot end blog: there is no blog started")

	def add_blog_post(self, url, json_post, first_post):
		if self.blog_started:
			post_text = ("        " + json.dumps({"post_url": url, "comments": json_post})).encode("utf-8")

			pre_text = b",\n" if not first_post else b""
			self.batch_file.write(pre_text + post_text)
		else:
			raise BatchError("Cannot add blog post: there is no blog started")


if __name__ == '__main__':

	test_posts = [
		{"id": "z12hdf5xirrcw1hok04ccljohpiyw5upazs0k", "type": 1001, "reply_count": 0, "date_posted": 1540770725763, "domain": "blogger.googleblog.com", "user_name": "austin mike", "user_id": "116544991436302200136", "user_avatar": "https://lh5.googleusercontent.com/-2SMs7hkstCY/AAAAAAAAAAI/AAAAAAAAABA/uJ_kS3C_dZU/photo.jpg", "user_profile": "./116544991436302200136", "plus_one_id": "4/jcsn4u34gsurkufmidlrigfchxpn0h33ghqaovvci1ormxtpipsa2ynna1pk/", "plus_one_count": 0, "text": [[[0, "Hello everyone. I was heartbroken because i had a small penis, not nice to satisfy a woman, i had so many relationship called off because of my situation, i have used so many product which i found online but none could offer me the help i searched for. i saw some few comments about this specialist called Dr OLU and decided to email him on drolusoutionhome@gmail.com"], [1], [0, "so I decided to give his herbal product a try. i emailed him and he got back to me, he gave me some comforting words with his herbal pills for Penis t, Enlargement Within 1 week of it, i began to feel the enlargement of my penis, \u201d and now it just 2 weeks of using his products my penis is about 9 inches longer and am so happy..feel free to contact DR OLU on(Drolusolutionhome@gmail.com) or Vist his websites for more information ["], [2, "http://droluherbs.clan.su/", None, ["http://droluherbs.clan.su/"]], [0, " ] or whatsapp him on this number +2348140654426"]]], "language_code": "en", "language_display": "English", "share_string": "s:updates:fountain:blogger.googleblog.com"},
		{"id":"z13dint5bznehbjj104cerabpr2pc1jg5kk0k","type":1001,"reply_count":0,"date_posted":1508225427212,"domain":"blogger.googleblog.com","user_name":"JAMIL HASHIM","user_id":"108946740664022095173","user_avatar":"https://lh4.googleusercontent.com/-5HfeqqrBU3s/AAAAAAAAAAI/AAAAAAAAEkA/pHt3oIHLxK4/photo.jpg","user_profile":"./108946740664022095173","plus_one_id":"4/jcsnat3dhtu3esnuhtmqksnehcsn0h33gpta2snkictb0stlhdnneuvfa1pk/","plus_one_count":0,"text":[[[0,"NICE SHARING..."]]],"language_code":"en","language_display":"English","share_string":"s:updates:fountain:blogger.googleblog.com"}
	]

	bf = BatchFile("../output/", 11273648)

	bf.start_blog(1, "googleblog", "https://blogger.googleblog.com", True)

	bf.add_blog_post("test123", json.dumps(test_posts[0]), False)
	bf.add_blog_post("test123", json.dumps(test_posts[1]), True)
	bf.end_blog()

	bf.start_blog(1, "afrmtbl", "https://afrmtbl.blogspot.com", False)

	bf.add_blog_post("test 1255553", json.dumps(test_posts[0]), False)
	bf.add_blog_post("test 1255553", json.dumps(test_posts[1]), True)

	bf.end_blog()
	bf.end_batch()