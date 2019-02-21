# https://security.stackexchange.com/questions/110539/how-does-including-a-magic-prefix-to-a-json-response-work-to-prevent-xssi-attack
# Google uses )]}'
def remove_xssi_guard(raw_response_text):
    return raw_response_text.replace(")]}\'", "")

def get_url_path(url):
    return url[url.rfind("/") + 1:url.rfind(".html")]