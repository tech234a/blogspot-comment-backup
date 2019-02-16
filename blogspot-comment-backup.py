import requests, json

def getbloginfo(blog):
    #Initialize variables for the while loop
    i = 0
    post_urls = []
    complete = False
    while complete == False:
        #Can only get 150 blog posts returned even if a higher number is specified
        url = blog + '/feeds/posts/default?max-results=150&alt=json&start-index=' + str((i * 150) + 1)
        print("getting url: " + url)
        requestinfo = requests.get(url)
        #Check if the blog exists and is accessible
        if requestinfo.status_code == 404: #Blog does not exist
            return "nf" #Blog not found
        elif requestinfo.status_code == 401: #Blog is private. Note: Blogs with content warnings do not seem to be blocked by these requests, so this error will *not* appear for those.
            return "pr" #Private blog
        elif not requestinfo.ok: #Any other error. Should really retry these requests.
            return "oe" #Other error
        else: #The blog is accessible, proceed in retreiving links
            feed_json = json.loads(requestinfo.text)
            post_urls.extend([feed_json['feed']['entry'][i]['link'][-1]['href'] for i in range(0, len(feed_json['feed']['entry']))])
            if len(feed_json['feed']['entry']) != 150:
                complete = True
            else:
                i+=1
    return post_urls #Return the complete list of articles

if __name__ == '__main__':
	#Sample default blog
	#A trailing slash on the URL seems to work OK, even if it processes with a double slash
	blog = 'https://googleblog.blogspot.com'#'https://blogger.googleblog.com'#'https://mytriptoamerica.blogspot.com'

	post_urls = getbloginfo(blog) #Retrieve the sample blog's articles
	print(f"Found {len(post_urls)} post links")
	print(post_urls)

#TODO:
#Report any of the above errors
#Check redirects for duplicate domains (if a custom domain is preferred, when searching for a blog by its regular name, it will automatically return the links under the custom domain, possibly redoing/duplicating work.
#Parse comment codes
