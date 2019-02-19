# blogspot-comment-backup
A project to archive comments from [blogspot](https://www.blogger.com/) blogs

### Resource Cost
A worst case example of the cost of getting a single comment (single page)

(top comment on [this post](https://apis.google.com/u/0/_/widget/render/comments?first_party_property=BLOGGER&query=https://blogger.googleblog.com/2019/01/an-update-on-google-and-blogger.html))

Replies | Comment +1ers | Reply +1ers | JSON Size (kB) | Estimated Network Requests | Elapsed Time (seconds)
------- | ----------- | --------- | -------------- | -------------------------- | ------------
❌ | ❌ | ❌ | 5   | 1 | ~1.73
❌ | ✔️ | ❌ | 31  | 2 | ~2.13
✔️ | ❌ | ❌ | 111 | 2 | ~2.37
✔️ | ✔️ | ❌ | 134 | 3 | ~2.80
✔️ | ❌ | ✔️ | 137 | 65 | ~3.10
✔️ | ✔️ | ✔️ | 160 | 66 | ~3.10
