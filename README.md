# blogspot-comment-backup
A project to archive comments from [blogspot](https://www.blogger.com/) blogs

### Resource Cost
A worst case example of the cost of getting a single comment (single page)

(top comment on [this post](https://apis.google.com/u/0/_/widget/render/comments?first_party_property=BLOGGER&query=https://blogger.googleblog.com/2019/01/an-update-on-google-and-blogger.html))

Replies | Comment +1ers | Reply +1ers | JSON Size (kB) | Estimated Network Requests | Elapsed Time (seconds)
------- | ----------- | --------- | -------------- | -------------------------- | ------------
❌ | ❌ | ❌ | 5   | 1 | ~1.81
❌ | ✔️ | ❌ | 31  | 2 | ~3.81
✔️ | ❌ | ❌ | 111 | 2 | ~2.50
✔️ | ✔️ | ❌ | 134 | 3 | ~4.42
✔️ | ❌ | ✔️ | 137 | 93 | ~21.00
✔️ | ✔️ | ✔️ | 160 | 94 | ~24.13
