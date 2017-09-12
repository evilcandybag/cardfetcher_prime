# -*- coding: utf-8 -*-
"""
Module with a lot of nifty functions for getting card data from the webernet
"""
import requests


def find_index_of_sequence(data, sequence, startindex=0):
    """find the index in a sequence"""
    index = startindex
    for token in sequence:
        index = data.find(token, index)
        if index == -1:
            return -1

    return index + len(sequence[-1])

def get_card_value(card_name, set_code):
    """get the monetary value of a card"""
    url = "http://www.mtggoldfish.com/widgets/autocard/%s [%s]" % (card_name, set_code)
    headers = {
        'Pragma': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6,sv;q=0.4',
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 6.1; WOW64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/48.0.2564.109 Safari/537.36'),
        'Accept': ('text/javascript, '
                    'application/javascript, '
                    'application/ecmascript, '
                    'application/x-ecmascript, '
                    '*/*; q=0.01'),
        'Referer': 'http://www.mtggoldfish.com/widgets/autocard/%s' % card_name,
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    response = requests.get(url, headers=headers)
    index = find_index_of_sequence(response.content, ["tcgplayer", "btn-shop-price", "$"])
    end_index = response.content.find("\\n", index)
    try:
        value = float(response.content[index+2:end_index].replace(",", ""))
    except ValueError:
        value = 0

    return value

def get_card(name):
    """fetch a card with the given name"""
    query_url = "http://api.deckbrew.com/mtg/cards?name=%s" % name
    print(query_url)
    r = requests.get(query_url)
    cards = r.json()

    if len(cards) < 1:
        return None

    card = cards[0]
    best_match = None
    for card_iter in cards:
        pos = card_iter["name"].lower().find(name)
        if best_match is None or (pos != -1 and pos < best_match):
            best_match = pos
            card = card_iter

    most_recent = card["editions"][0]
    card["value"] = get_card_value(card["name"], most_recent["set_id"])

    return card

def emoji_filter(indata):
    """add mana symbols as emoji tags to a message"""
    ret = indata.replace("{", ":_")
    ret = ret.replace("}", "_:")
    lastpos = None
    while ret.rfind(":_", 0, lastpos) != -1:
        lastpos = ret.rfind(":_", 0, lastpos)
        start = lastpos + 2
        end = ret.rfind("_:")
        content = ret[start:end]
        content = content.lower()
        content = content.replace("/", "")
        ret = ret[:start] + content + ret[end:]

    return ret

def parse_card_tags(indata):
    """parse a string and return all tags contained within"""
    bang_trigger = "!card "
    card_tag_open = "[["
    card_tag_end = "]]"

    trigger_index = indata.find(bang_trigger)
    if trigger_index > -1:
        return [indata[trigger_index + len(bang_trigger):]]

    all_tags = []
    remaining = indata
    while True:
        tag_open_index = remaining.find(card_tag_open)
        tag_end_index = remaining.find(card_tag_end)
        if tag_open_index > -1 and tag_end_index > -1 and tag_end_index > tag_open_index:
            tag = remaining[tag_open_index + len(card_tag_open):tag_end_index]
            all_tags.append(tag)
            remaining = remaining[tag_end_index + len(card_tag_end):]
        else:
            break
    return all_tags



ORACLE_TRIGGER = "!oracle "
PRICE_TRIGGER = "!price "
CR_TRIGGER = "!cr "

def parse_for_card_input(slack_client, indata):
    """parse a user message and output something to the supplied slack client"""
    if indata.has_key("text"):
        userinput = indata["text"].lower()

        attachments = ""
        text = ""
        not_found = "No results found"

        all_tags = parse_card_tags(userinput)
        if all_tags: #false if empty
            temp_text = ""
            temp_attachments = []
            for search_term in all_tags:
                card = get_card(search_term)
                if not card:
                    temp_text += "No result for %s\n" % search_term
                else:
                    most_recent_printing = card["editions"][0]
                    header = "Latest printing for %s is %s\n" % (
                        card["name"], most_recent_printing["set"])
                    temp_attachments.append('{"image_url":"%s","title":"%s"}'% (
                        most_recent_printing["image_url"], card["name"].replace("\"", "\\\"")))
                    temp_text += header

            text += temp_text
            attachments += "[%s]" % (",".join(temp_attachments))

        if userinput.find(ORACLE_TRIGGER) > -1:
            search_term = userinput[userinput.find(ORACLE_TRIGGER) + len(ORACLE_TRIGGER):]
            card = get_card(search_term)
            if not card:
                text += not_found
            else:
                most_recent_printing = card["editions"][0]
                typeline = ""
                if card.has_key("supertypes"):
                    for supertype in card["supertypes"]:
                        typeline += supertype.capitalize() + " "
                if card.has_key("types"):
                    for cardtype in card["types"]:
                        typeline += cardtype.capitalize() + " "
                    if card.has_key("subtypes"):
                        typeline += "- "
                if card.has_key("subtypes"):
                    for subtype in card["subtypes"]:
                        typeline += subtype.capitalize() + " "

                answer = "%s\t\t%s\n%s\n%s" % (
                    card["name"],
                    emoji_filter(card["cost"]),
                    typeline, emoji_filter(card["text"]))

                valueinfo = ""
                if card.has_key("power") and card.has_key("toughness"):
                    answer += "\n*`%s/%s`*" % (card["power"], card["toughness"])
                if card["value"] > 0:
                    valueinfo = "\n\nCurrent market price for most recent printing (%s) - $%.1f" % (
                        most_recent_printing["set"], card["value"])

                answer += valueinfo
                text += answer

        if userinput.find(PRICE_TRIGGER) > -1:
            search_term = userinput[userinput.find(PRICE_TRIGGER) + len(PRICE_TRIGGER):]
            card = get_card(search_term)
            if not card:
                text += not_found
            else:
                most_recent_printing = card["editions"][0]
                answer = "Unable to find price information for %s" % card["name"]
                if card["value"] > 0:
                    answer = "Current market price for most recent printing of %s (%s) - $%.1f" % (
                        card["name"],
                        most_recent_printing["set"],
                        card["value"])

                text += answer

        if userinput.find(CR_TRIGGER) > -1:
            search_term = userinput[userinput.find(CR_TRIGGER) + len(CR_TRIGGER):]
            rule = get_rule(search_term)
            if rule:
                answer = "%s - %s" % (search_term, rule)
            else:
                answer = "No result found"
            text += answer

        if text or attachments:
            slack_client.rtm.api_call(
                "chat.postMessage",
                channel=indata["channel"],
                attachments=attachments,
                text=text,
                as_user=True)

COMP_RULES_URL = "http://media.wizards.com/2016/docs/MagicCompRules_04082016.txt"
COMP_RULES_LOOKUP = {}


def get_comp_rules():
    """ Get cached competition rules"""
    response = requests.get(COMP_RULES_URL)
    rules = response.text.encode("utf-8")
    for rule in rules.split("\n"):
        COMP_RULES_LOOKUP[rule.split(" ")[0]] = (
            " ".join(rule.split(" ")[1:])).decode("Windows.1252").replace(u"Â", "")
    return COMP_RULES_LOOKUP

def get_rule(rule_key):
    """get the rule with the given key"""
    if rule_key not in COMP_RULES_LOOKUP:
        if rule_key[-1:] == ".":
            rule_key = rule_key[:-1]
    if rule_key not in COMP_RULES_LOOKUP:
        rule_key += "."
    if rule_key not in COMP_RULES_LOOKUP:
        return None
    return COMP_RULES_LOOKUP[rule_key]
