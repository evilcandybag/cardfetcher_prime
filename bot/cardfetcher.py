# -*- coding: utf-8 -*-

import json
import requests


def findIndexOfSequence(data, sequence, startindex = 0):
    index = startindex
    for token in sequence:
        index = data.find(token, index)
        if index == -1:
            return -1

    return index + len(sequence[-1])

def getCardValue(cardName, setCode):
    url = "http://www.mtggoldfish.com/widgets/autocard/%s [%s]" % (cardName, setCode)
    headers = {
        'Pragma': 'no-cache',
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6,sv;q=0.4',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36',
        'Accept': 'text/javascript, application/javascript, application/ecmascript, application/x-ecmascript, */*; q=0.01',
        'Referer': 'http://www.mtggoldfish.com/widgets/autocard/%s' % cardName,
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    response = requests.get(url, headers=headers)
    index = findIndexOfSequence(response.content, ["tcgplayer", "btn-shop-price", "$"])
    endIndex = response.content.find("\\n", index)
    try:
        value = float(response.content[index+2:endIndex].replace(",", ""))
    except ValueError:
        value = 0

    return value

def getCard(name):
    queryUrl = "http://api.deckbrew.com/mtg/cards?name=%s" % name
    print(queryUrl)
    r = requests.get(queryUrl)
    cards = r.json()

    if len(cards) < 1:
        return None

    card = cards[0]
    bestMatch = None
    for cardIter in cards:
        pos = cardIter["name"].lower().find(name)
        if bestMatch is None or (pos != -1 and pos < bestMatch):
            bestMatch = pos
            card = cardIter

    mostRecent = card["editions"][0]
    card["value"] = getCardValue(card["name"], mostRecent["set_id"])

    return card

def getPlaneswalker(dciNumber):
    url = "http://www.wizards.com/Magic/PlaneswalkerPoints/JavaScript/GetPointsHistoryModal"
    headers = {
        'Pragma': 'no-cache',
        'Origin': 'http://www.wizards.com',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8,de;q=0.6,sv;q=0.4',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': 'f5_cspm=1234; BIGipServerWWWPWPPOOL01=353569034.20480.0000; __utmt=1; BIGipServerWWWPool1=3792701706.20480.0000; PlaneswalkerPointsSettings=0=0&lastviewed=9212399887; __utma=75931667.1475261136.1456488297.1456488297.1456488297.1; __utmb=75931667.5.10.1456488297; __utmc=75931667; __utmz=75931667.1456488297.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
        'Connection': 'keep-alive',
        'Referer': 'http://www.wizards.com/Magic/PlaneswalkerPoints/%s' % dciNumber
    }
    data = {"Parameters":{"DCINumber":dciNumber,"SelectedType":"Yearly"}}
    response = requests.post(url, headers=headers, data=json.dumps(data))

    seasons = []

    responseData = json.loads(response.content)
    markup = responseData["ModalContent"]
    searchPosition = markup.find("SeasonRange")

    while searchPosition != -1:
        pointsvalue = "PointsValue\">"
        searchPosition = markup.find(pointsvalue, searchPosition)
        searchPosition += len(pointsvalue)
        endPosition = markup.find("</div>", searchPosition)
        if endPosition != -1:
            value = markup[searchPosition:endPosition]
            seasons.append(int(value))
        searchPosition = markup.find("SeasonRange", searchPosition)

    return {"currentSeason": seasons[0], "lastSeason": seasons[1]}

def getPlaneswalkerByes(walker):
    if walker["currentSeason"] >= 2250 or walker["lastSeason"] >= 2250:
        return 2
    elif walker["currentSeason"] >= 1300 or walker["lastSeason"] >= 1300:
        return 1

    return 0

def emojiFilter(indata):
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

def parseForCardInput(sc, indata):
    if indata.has_key("text"):
        userinput = indata["text"].lower()

        cardTrigger = "!card "
        attachments = ""
        text = ""
        notFound = "No results found"

        if userinput.find(cardTrigger) > -1:
            searchTerm = userinput[userinput.find(cardTrigger) + len(cardTrigger):]
            card = getCard(searchTerm)
            if not card:
                text += notFound
            else:
                mostRecentPrinting = card["editions"][0]
                valueinfo = ""
                if card["value"] > 0:
                    valueinfo = "\n\nCurrent market price for most recent printing (%s) $%.1f" % (mostRecentPrinting["set"], card["value"])

                attachments += '[{"image_url":"%s","title":"%s"}]' % (mostRecentPrinting["image_url"], card["name"].replace("\"", "\\\""))
                text += valueinfo

        oracleTrigger = "!oracle "
        if userinput.find(oracleTrigger) > -1:
            searchTerm = userinput[userinput.find(oracleTrigger) + len(oracleTrigger):]
            card = getCard(searchTerm)
            if not card:
                text += notFound
            else:
                mostRecentPrinting = card["editions"][0]
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
                answer = "%s\t\t%s\n%s\n%s" % (card["name"], emojiFilter(card["cost"]), typeline, emojiFilter(card["text"]))
                valueinfo = ""
                if card.has_key("power") and card.has_key("toughness"):
                    answer += "\n*`%s/%s`*" % (card["power"], card["toughness"])
                if card["value"] > 0:
                    valueinfo = "\n\nCurrent market price for most recent printing (%s) - $%.1f" % (mostRecentPrinting["set"], card["value"])

                answer += valueinfo
                text += answer

        priceTrigger = "!price "
        if userinput.find(priceTrigger) > -1:
            searchTerm = userinput[userinput.find(priceTrigger) + len(priceTrigger):]
            card = getCard(searchTerm)
            if not card:
                text += notFound
            else:
                mostRecentPrinting = card["editions"][0]
                answer = "Unable to find price information for %s" % card["name"]
                if card["value"] > 0:
                    answer = "Current market price for most recent printing of %s (%s) - $%.1f" % (card["name"], mostRecentPrinting["set"], card["value"])

                text += answer

        pwpTrigger = "!pwp "
        if userinput.find(pwpTrigger) > -1:
            searchTerm = userinput[userinput.find(pwpTrigger) + len(pwpTrigger):]
            planeswalker = getPlaneswalker(searchTerm)
            answer = "DCI# %s has %s points in the current season, %s points last season\nCurrently " % (searchTerm, planeswalker["currentSeason"], planeswalker["lastSeason"])
            byes = getPlaneswalkerByes(planeswalker)
            if not byes:
                answer += "not eligible for GP byes"
            else:
                answer += "eligible for %d GP byes" % byes

            text += answer

        crTrigger = "!cr "
        if userinput.find(crTrigger) > -1:
            searchTerm = userinput[userinput.find(crTrigger) + len(crTrigger):]
            rule = getRule(searchTerm)
            if rule:
                answer = "%s - %s" % (searchTerm, rule)
            else:
                answer = "No result found"
            text += answer

        if text or attachments:
            sc.api_call(
                "chat.postMessage",
                channel=indata["channel"],
                attachments=attachments,
                text=text,
                as_user=True)

compRulesUrl = "http://media.wizards.com/2016/docs/MagicCompRules_04082016.txt"
compRulesLookup = {}

def getCompRules():
    r = requests.get(compRulesUrl)
    rules = r.text.encode("utf-8")
    for rule in rules.split("\n"):
        compRulesLookup[rule.split(" ")[0]] = (" ".join(rule.split(" ")[1:])).decode("Windows.1252").replace(u"Â","")
    return compRulesLookup

def getRule(ruleKey):
    if ruleKey not in compRulesLookup:
        if ruleKey[-1:] == ".":
            ruleKey = ruleKey[:-1]
    if ruleKey not in compRulesLookup:
        ruleKey += "."
    if ruleKey not in compRulesLookup:
        return None
    return compRulesLookup[ruleKey]
