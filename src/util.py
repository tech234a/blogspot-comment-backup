# https://stackoverflow.com/questions/29991917/indices-of-matching-parentheses-in-python
def get_bracket_pairs(text):
    istart = [] # stack of indices of opening parentheses
    d = {}

    for i, c in enumerate(text):
        if c == "[":
             istart.append(i)
        if c == "]":
            try:
                d[istart.pop()] = i
            except IndexError:
                print("Too many closing parentheses")
    if istart: # check if stack is empty afterwards
        print("Too many opening parentheses")

    return d

# https://security.stackexchange.com/questions/110539/how-does-including-a-magic-prefix-to-a-json-response-work-to-prevent-xssi-attack
# Google uses )]}'
def remove_xssi_guard(raw_response_text):
    return raw_response_text.replace(")]}\'", "")

def get_url_path(url):
    return url[url.rfind("/") + 1:url.rfind(".html")]