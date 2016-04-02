import uuid, hashlib, urllib, re, os
from DumbTools import DumbKeyboard

PREFIX = "/video/couchpotato"

NAME = L('CouchPotato')

ART           = 'art-default.jpg'
ICON          = 'icon-default.png'
SEARCH_ICON   = 'icon-search.png'
PREFS_ICON    = 'icon-prefs.png'
SNATCHED_ICON = 'sab-icon.png'
DL_ICON       = 'Plex_256x256.png'
MOVIE_ICON    = 'movie-reel.jpg'
THEATRE_ICON  = 'popcorn.jpg'
BD_ICON       = 'BD_icon.jpg'

####################################################################################################

def Start():
    
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    ObjectContainer.art = R(ART)
    ObjectContainer.title1 = NAME
    DirectoryObject.thumb = R(ICON)
    HTTP.CacheTime=3600

####################################################################################################
@route('%s/header' % PREFIX)
def AuthHeader():
    header = {}

    if Prefs['cpUser'] and Prefs['cpPass']:
        header = {'Authorization': 'Basic ' + String.Base64Encode(Prefs['cpUser'] + ':' + Prefs['cpPass'])}

    return header

####################################################################################################
@route('%s/validate' % PREFIX)
def ValidatePrefs():
    if Prefs['cpUser'] and Prefs['cpPass']:
        try:
            Dict['ApiKey'] = Get_CP_API_KEY()
            Log.Debug("CouchPotato API key stored for future use.")
            return
        except:
            return ObjectContainer(header="Unable to retrieve API key", message="Please confirm that your settings are correct.")

####################################################################################################
@handler(PREFIX, NAME, ICON, ART)
def MainMenu():
    '''Populate main menu options'''
    oc = ObjectContainer(view_group="InfoList", no_cache=True)
    
    if CP_API_KEY() != 'notfound':
        oc.add(DirectoryObject(key=Callback(MoviesMenu), title="Manage your movies list",
            summary="View and edit your CouchPotato wanted movies list",thumb=R(ICON)))
        oc.add(DirectoryObject(key=Callback(ComingSoonMenu), title="Coming Soon",
            summary="Browse upcoming movies and add them to your wanted list", thumb=R("RT-icon.png")))
        if Client.Product in DumbKeyboard.clients:
            DumbKeyboard(PREFIX, oc, Search, dktitle="Search for Movies", dkthumb=R(SEARCH_ICON))
        else:
            oc.add(InputDirectoryObject(key=Callback(Search), title="Search for Movies",
                                        summary="Find movies to add to your wanted list", prompt="Search for",
                                        thumb=R(SEARCH_ICON), ))
        oc.add(DirectoryObject(key=Callback(Suggestions), title="Suggestions",
            summary="Movies suggested by CouchPotato", thumb=R(ICON)))
    
    oc.add(PrefsObject(title="Preferences", summary="Set prefs to allow plugin to connect to CouchPotato app",thumb=R(PREFS_ICON)))
    
    return oc

################################################################################
@route('%s/movies' % PREFIX)
def MoviesMenu():
    '''Populate the movies menu with available options'''
    oc = ObjectContainer(view_group="InfoList", title2="Wanted Movies")

    oc.add(DirectoryObject(key=Callback(WantedMenu), title="Wanted List",
        summary="CouchPotato is watching for these movies",thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(SnatchedMenu), title="Snatched List",
        summary="CouchPotato has found these movies and is waiting for them to be downloaded.", thumb=R(SNATCHED_ICON)))
    oc.add(DirectoryObject(key=Callback(DownloadedMenu), title="Downloaded",
        summary="CouchPotato has found and downloaded all these movies in the quality you requested. They should be available in your Plex library.", thumb=R(DL_ICON)))
    return oc
    
################################################################################
@route('%s/wanted' % PREFIX)
def WantedMenu():

    oc = ObjectContainer(view_group="InfoList", title2="Wanted", no_cache=True)
    thumbDefault = ''
    summaryDefault = 'This movie is waiting to be available.'
    cpResult = CP_API_CALL('movie.list',{'status':'active'})
    
    for item in cpResult['movies']:
        try:
            info = item['info']
            title = item['title']
            try: summary = info['plot']
            except: summary = summaryDefault
            year = info['year']
            dataID = item['_id']
            title = title + ' (%s)' % year
            oc.add(PopupDirectoryObject(key=Callback(WantedList, dataID=dataID), title=title, summary=summary, thumb=Callback(GetPoster, images=info['images'])))
        except:
            Log("Skipping item due to parsing error.\n%s" % item)
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc
    

  
################################################################################
@route('%s/snatched' % PREFIX)
def SnatchedMenu():

    oc = ObjectContainer(view_group="InfoList", title2="Snatched", no_cache=True)
    thumbDefault = R(SNATCHED_ICON)
    summaryDefault = 'This movie should now appear in your downloads queue.'
    cpResult = CP_API_CALL('movie.list',{'release_status':'snatched'})
        
    for item in cpResult['movies']:
        try:
            info = item['info']
            title = item['title']
            try: summary = info['plot']
            except: summary = summaryDefault
            year = info['year']
            dataID = item['_id']
            title = title + ' (%s)' % year
            oc.add(PopupDirectoryObject(key=Callback(SnatchedList, dataID=dataID), title=title, summary=summary, thumb=Callback(GetPoster, images=info['images'])))
        except:
            Log("Skipping item due to parsing error.\n%s" % item)
        
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc
  
################################################################################
@route('%s/downloaded' % PREFIX, offset=int)
def DownloadedMenu(offset=0):

    oc = ObjectContainer(view_group="InfoList", title2="Downloaded", no_cache=True)
    thumbDefault = R(DL_ICON)
    summaryDefault = 'This movie should now be available in your Plex library.'
    cpResult = CP_API_CALL('movie.list',{'status':'done'})
    
    for item in cpResult['movies'][offset:offset+20]:
        try:
            info = item['info']
            title = item['title']
            try: summary = info['plot']
            except: summary = summaryDefault
            year = info['year']
            dataID = item['_id']
            title = title + ' (%s)' % year
            oc.add(PopupDirectoryObject(key=Callback(SnatchedList, dataID=dataID), title=title, summary=summary, thumb=Callback(GetPoster, images=info['images'])))
        except:
            Log("Skipping item due to parsing error.\n%s" % item)
        
    if len(cpResult['movies']) > (offset+20):
        oc.add(NextPageObject(key=Callback(DownloadedMenu, offset=offset+20)))
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc

################################################################################
@route('%s/wantedpopup' % PREFIX)
def WantedList(dataID):
    '''Display an action-context menu for the selected movie'''
    oc = ObjectContainer(title2="Wanted Movies")
    oc.add(DirectoryObject(key=Callback(ForceRefresh, dataID=dataID), title='Refresh'))
    oc.add(DirectoryObject(key=Callback(RemoveMovie, dataID=dataID), title='Delete'))
    return oc

################################################################################
@route('%s/snatchedpopup' % PREFIX)
def SnatchedList(dataID):
    '''Display an action-context menu for the selected movie'''
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(FailedFindNew, dataID=dataID), title='Failed - Find New Source'))
    return oc

################################################################################
@route('%s/refresh' % PREFIX)
def ForceRefresh(dataID):
    cpResult = CP_API_CALL('movie.refresh',{'id':dataID})
    return ObjectContainer(header="CouchPotato", message=L('Forcing refresh/search'), no_history=True)

################################################################################
@route('%s/remove' % PREFIX)
def RemoveMovie(dataID):
    '''Tell CouchPotato to remove the selected movie from the wanted list'''
    cpResult = CP_API_CALL('movie.delete',{'id':dataID})
    return ObjectContainer(header="CouchPotato", message=L('Deleting from wanted list'), no_history=True)

################################################################################
@route('%s/findnew' % PREFIX)
def FailedFindNew(dataID):
    '''Tell CouchPotato to mark the selected movie as a failed download and find a different file to retry'''
    cpResult = CP_API_CALL('searcher.try_next',{'id':dataID})
    return ObjectContainer(header="CouchPotato", message=L('Movie re-added to "Wanted" list'), no_history=True)

################################################################################
@route('%s/search' % PREFIX)
def Search(query):
    '''Request search results from CouchPotato. Requires CP v2'''
    oc = ObjectContainer(title2="Search Results", view_group="InfoList")
    Log.Debug('Search term(s): ' + query)
    
    resultList = CP_API_CALL('movie.search',{'q':String.Quote(query, usePlus=True)})
    resultCount = 0
    
    for movie in resultList['movies']:
        Log.Debug(movie)
        if resultCount < 10:
            movieTitle = movie['original_title']
            try:
                imdbID = movie['imdb']
            except:
                imdbID = movie['tmdb_id']
            try:
                year = movie['year']
                title = "%s (%s)" % (movieTitle, year)
            except:
                year = None
                title = movieTitle
            try:
                overview = movie['plot']
            except:
                overview = ""
            try:
                posterUrl = movie['images']['poster_original'][0]
            except:
                posterUrl = 'None'
            
            oc.add(PopupDirectoryObject(key=Callback(AddMovieMenu, imdbID=imdbID, suggestion=False),
                    title = title, summary=overview,
                    thumb = Resource.ContentsOfURLWithFallback(url=posterUrl, fallback='no_poster.jpg')))
            resultCount = resultCount+1
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc
    
################################################################################
@route('%s/addmenu' % PREFIX)
def AddMovieMenu(imdbID, suggestion=True):
    '''Display an action/context menu for the selected movie'''
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(AddMovie, imdbID=imdbID, suggestion=suggestion), title='Add to Wanted list'))
    oc.add(DirectoryObject(key=Callback(QualitySelectMenu, imdbID=imdbID, suggestion=suggestion), title='Select quality to add'))
    return oc

################################################################################
@route('%s/add' % PREFIX)
def AddMovie(imdbID, suggestion=True):
    '''Tell CouchPotato to add the selected movie to the wanted list'''
    cpResult = CP_API_CALL('movie.add',{'identifier':imdbID})
    if suggestion:
        if cpResult['success']:
            removeFromSuggestions = CP_API_CALL('suggestion.ignore',{'imdb':imdbID, 'remove_only':True})
    
    return ObjectContainer(header="CouchPotato", message=L("Added to Wanted list."), no_history=True)

################################################################################
@route('%s/cpurl' % PREFIX)
def Get_CP_URL():
    cpUrlBase = Prefs['cpURLBase']
    if cpUrlBase:
        if cpUrlBase[0] != '/':
           cpUrlBase = '/' + cpUrlBase
    else:
        cpUrlBase = ''
    if Prefs['cpIP'].startswith("http"):
        return '%s:%s%s' % (Prefs['cpIP'], Prefs['cpPort'], cpUrlBase)
    else:
        if Prefs['https']:
            return 'https://%s:%s%s' % (Prefs['cpIP'], Prefs['cpPort'], cpUrlBase)
        else:
            return 'http://%s:%s%s' % (Prefs['cpIP'], Prefs['cpPort'], cpUrlBase)
  
################################################################################
@route('%s/cpapikey' % PREFIX)
def CP_API_KEY():
    if Dict['ApiKey'] == None or Dict['ApiKey'] == 'notfound':
        Dict['ApiKey'] = Get_CP_API_KEY()
        return Dict['ApiKey']
    else:
        return Dict['ApiKey']
    
################################################################################
@route('%s/getapikey' % PREFIX)
def Get_CP_API_KEY():
    try: mUser = hashlib.md5(Prefs['cpUser']).hexdigest()
    except: mUser = ''
    try: mPass = hashlib.md5(Prefs['cpPass']).hexdigest()
    except: mPass = ''
    url = Get_CP_URL()+'/getkey/?p='+mPass+'&u='+mUser
    Log.Debug('API_KEY_URL: '+url)
    try: cpResult = JSON.ObjectFromURL(url)
    except:
        Log.Debug('ERROR: Unable to load API Key')
        cpResult = {'api_key':'notfound'}
    return cpResult['api_key']

################################################################################
@route('%s/apiurl' % PREFIX, command=str, apiParm=dict, apiFile=str, apiCache=bool)
def CP_API_URL(command, apiParm={}, apiFile='', apiCache=False):
    if not apiCache:
        apiParm['nocache_uuid'] = uuid.uuid1()
    cpParams = urllib.urlencode(apiParm)
    if len(str(cpParams)) > 0:
        cpParams = '?'+str(cpParams)
    apiKey = CP_API_KEY()
    apiUrl = Get_CP_URL()+'/api/'+str(apiKey)+'/'+str(command)+'/'+str(apiFile)+cpParams
    Log.Debug('API_URL:'+apiUrl)
    return apiUrl
    
################################################################################
@route('%s/api' % PREFIX, command=str, apiParm=dict, apiFile=str, apiCache=bool)
def CP_API_CALL(command, apiParm={}, apiFile='', apiCache=False):
    try: cpResult = JSON.ObjectFromURL(CP_API_URL(command, apiParm, apiFile, apiCache))
    except:
        #Log the failure
        Log.Debug('FAILED API CALL:'+command)
        cpResult = {'success':False,'error':'Bad result from CP server'}
        #Reset the stored api key to force user to check prefs
        Log.Debug('Resetting stored API key')
        Dict['ApiKey'] = 'notfound'
    return cpResult

################################################################################
@route('%s/poster' % PREFIX, images=dict)
def GetPoster(images):
    poster = None
    try: poster = images['poster_original'][-1]
    except: poster = images['poster']
    if not poster:
        poster = R('no_poster.jpg')
    return Redirect(poster)
    
################################################################################
@route('%s/qualities' % PREFIX)
def QualitySelectMenu(imdbID, suggestion=None):
    '''provide an option to select a quality other than default before adding a movie'''
    oc = ObjectContainer()
    #CP v2 mode
    cpResult = CP_API_CALL('profile.list')
        
    for quality in cpResult['list']:
        name = quality['label']
        value = quality['_id']
        oc.add(DirectoryObject(key=Callback(AddWithQuality, imdbID=imdbID, quality=value, suggestion=suggestion),
            title=name, summary='Add movie with '+name+' quality profile', thumb=R(ICON)))
        
    return oc

################################################################################
@route('%s/addquality' % PREFIX)
def AddWithQuality(imdbID, quality, suggestion):   
    '''tell CouchPotato to add the given movie with the given quality (rather than the defaultQuality)'''
    cpResult = CP_API_CALL('movie.add',{'identifier':imdbID, 'profile_id':quality})
    if suggestion:
        if cpResult['success']:
            removeFromSuggestions = CP_API_CALL('suggestion.ignore',{'imdb':imdbID, 'remove_only':True})
    
    return ObjectContainer(header="CouchPotato", message=L("Added to Wanted list."), no_history=True)

################################################################################
@route('%s/suggestions' % PREFIX)
def Suggestions():
    oc = ObjectContainer(title2="Suggestions", no_cache=True)
    cpResult = CP_API_CALL('suggestion.view')
    for movie in cpResult['suggestions']:
        title = movie['original_title']
        summary = movie['plot']
        try: year = movie['year']
        except: year = None
        thumbs = movie['images']['poster_original'] + movie['images']['poster']

        try:
            imdbID = movie['imdb']
            if imdbID == '': raise e
        except:
            imdbID = movie['tmdb_id']
        oc.add(PopupDirectoryObject(key=Callback(SuggestionMenu, imdbID=imdbID, title=title, year=year),
                    title = title, summary=summary,
                    thumb = Resource.ContentsOfURLWithFallback(url=thumbs, fallback='no_poster.jpg')))
    return oc

################################################################################
@route('%s/suggestions/menu' % PREFIX)
def SuggestionMenu(imdbID, title, year):
    oc = AddMovieMenu(imdbID, suggestion=True)
    oc.add(DirectoryObject(key=Callback(FindTrailer, title=title, year=year), title="Watch Trailer"))
    oc.add(DirectoryObject(key=Callback(IgnoreSuggestion, imdbID=imdbID), title = "Ignore this suggestion"))
    oc.add(DirectoryObject(key=Callback(IgnoreSuggestion, imdbID=imdbID, seenIt=True), title = "Seen it, Like it, don't add."))
    return oc

################################################################################
@route('%s/suggestions/ignore' % PREFIX)
def IgnoreSuggestion(imdbID, seenIt=None):
    '''tell CouchPotato to remove the given movie from the list of suggestions'''
    if seenIt:
        cpResult = CP_API_CALL('suggestion.ignore',{'imdb':imdbID, 'mark_seen':1})
        return ObjectContainer(header="CouchPotato", message=L("Suggestion removed from list."), no_history=True)
    else:
        cpResult = CP_API_CALL('suggestion.ignore',{'imdb':imdbID})
        return ObjectContainer(header="CouchPotato", message=L("Suggestion ignored."), no_history=True)

################################################################################
@route('%s/suggestions/trailer' % PREFIX)
def FindTrailer(title, year):
    oc = ObjectContainer(title2 = "%s - Trailer" % title)
    trailer_url = 'https://gdata.youtube.com/feeds/videos?vq=%s&max-results=1&alt=json-in-script&orderby=relevance&sortorder=descending&format=5&fmt=18'
    if year:
        trailer_query = '"%s" %s trailer' % (title, year)
    else:
        trailer_query = '"%s" trailer' % title
    result = HTTP.Request(trailer_url % String.Quote(trailer_query)).content.strip('gdata.io.handleScriptLoaded(')[:-2]
    yt_data = JSON.ObjectFromString(result)
    trailer_id = yt_data['feed']['entry'][0]['id']['$t'].split('/')[-1]
    trailer_url = 'http://youtube.com/watch?v=' + trailer_id
    oc.add(URLService.MetadataObjectForURL(trailer_url))
    return oc

####################################################################################################
####################################################################################################
####################################################################################################


RT_API_KEY = 'bnant4epk25tfe8mkhgt4ezg'

RT_LIST_URL = 'http://api.rottentomatoes.com/api/public/v1.0/lists/%s.json?apikey=%s'

####################################################################################################
@route('%s/soon' % PREFIX)
def ComingSoonMenu():
    oc = ObjectContainer(title2="Coming Soon")
    oc.add(DirectoryObject(key=Callback(ComingMoviesListMenu, list_type="movies"), title="Theatres", thumb=R("RT-icon.png")))
    oc.add(DirectoryObject(key=Callback(ComingMoviesListMenu, list_type="dvds"), title="DVD", thumb=R("RT-icon.png")))
    return oc

@route('%s/soonlist' % PREFIX)
def ComingMoviesListMenu(list_type):
    oc = ObjectContainer()
    if list_type == "movies":
        oc.title2="Theaters"
    elif list_type == "dvds":
        oc.title2 == "DVD"
    
    movieLists = JSON.ObjectFromURL(RT_LIST_URL % (list_type, RT_API_KEY))
    for movie_list in movieLists['links']:
        name = movie_list
        title = String.CapitalizeWords(name.replace('_', ' '))
        url = movieLists['links'][name]
        oc.add(DirectoryObject(key=Callback(ComingMoviesList, title=title, url=url), title=title, thumb=R(ICON)))
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc

@route('%s/comingmovies' % PREFIX)  
def ComingMoviesList(title, url=None):
    oc = ObjectContainer(title2=title, view_group="InfoList")
    
    movies = JSON.ObjectFromURL(url + '?apikey=%s' % RT_API_KEY)
    
    for movie in movies['movies']:
        title = "%s (%s)" % (movie['title'], movie['year'])
        summary = BuildSummary(movie)
        thumb= movie['posters']['original']
        
        oc.add(PopupDirectoryObject(key=Callback(DetailsMenu, movie=movie), title=title, summary=summary, thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc

@route('%s/details' % PREFIX, movie=dict)
def DetailsMenu(movie):
    oc = ObjectContainer(title2=movie['title'])
    thumb = movie['posters']['original']
    imdb_ttid = 'tt'+str(movie['alternate_ids']['imdb'])
    oc.add(DirectoryObject(key=Callback(AddMovie, imdbID=imdb_ttid), title='Add to Wanted list', thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    oc.add(DirectoryObject(key=Callback(QualitySelectMenu, imdbID=imdb_ttid), title='Select quality to add', thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    oc.add(DirectoryObject(key=Callback(ReviewsMenu, title=movie['title'], url=movie['links']['reviews']), title="Read Reviews", thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    oc.add(DirectoryObject(key=Callback(TrailersMenu, title=movie['title'], url=movie['links']['reviews'].replace('reviews.json','clips.json')), title="Watch Trailers", thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    if len(ComingMoviesList(title=movie['title'], url=movie['links']['similar'])) > 0:
        oc.add(DirectoryObject(key=Callback(ComingMoviesList, title=movie['title'], url=movie['links']['similar']), title="Find Similar Movies", thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    return oc

@route('%s/reviews' % PREFIX)
def ReviewsMenu(title, url):
    oc = ObjectContainer(title1=title, title2="Reviews", view_group="InfoList")
    reviews = JSON.ObjectFromURL(url +'?apikey=%s' % RT_API_KEY)['reviews']
    for review in reviews:
        title = "%s - %s" % (review['critic'], review['publication'])
        try: score = review['original_score']
        except: score = 'N/A'
        summary = "Rating: %s\n\n%s" % (score, review['quote'])
        oc.add(DirectoryObject(key=Callback(DoNothing), title=title, summary=summary, thumb=None))
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc

@route('%s/trailers' % PREFIX)
def TrailersMenu(title, url):
    oc = ObjectContainer(title1=title, title2="Trailers", view_group="InfoList")
    trailers = JSON.ObjectFromURL(url +'?apikey=%s' % RT_API_KEY)['clips']
    for trailer in trailers:
        #Log.Debug(trailer)
        title = trailer['title']
        thumb = trailer['thumbnail']
        duration = int(trailer['duration'])*1000
        url = trailer['links']['alternate']
        oc.add(VideoClipObject(url=url, title=title, duration=duration, thumb = Resource.ContentsOfURLWithFallback(url=thumb, fallback='no_poster.jpg')))
    
    if len(oc) < 1:
        return ObjectContainer(header="No items to display", message="This directory appears to be empty.")
    else:
        return oc

@route('%s/cast' % PREFIX, cast=dict)
def GetCast(cast):
    actors = ''
    for actor in cast:
        name = actor['name']
        try: role = actor['characters'][0]
        except: role = ''
        actors = actors + '%s - %s\n' % (name, role)
    return actors

@route('%s/releasedates' % PREFIX, movie=dict)
def GetReleaseDates(movie):
    try: theater = movie['release_dates']['theater']
    except: theater = 'N/A'
    try: dvd = movie['release_dates']['dvd']
    except: dvd = 'N/A'
    return "Theater: %s\nDVD: %s" % (theater, dvd)

@route('%s/summary' % PREFIX, movie=dict)
def BuildSummary(movie):
    critic_rating = movie['ratings']['critics_score']
    if critic_rating == -1:
        critic_rating = "None"
    audience_rating = movie['ratings']['audience_score']
    cast = GetCast(movie['abridged_cast'])
    synopsis = movie['synopsis']
    content_rating = movie['mpaa_rating']
    runtime = movie['runtime']
    release_dates = GetReleaseDates(movie)
    summary = 'Runtime: %s minutes\nMPAA: %s\nCritic Rating: %s\nAudience Rating: %s\nRelease:\n%s\n\nSynopsis:\n%s\n\nCast:\n%s' % (runtime, content_rating, critic_rating, audience_rating, release_dates, synopsis, cast)
    return summary

@route('%s/empty' % PREFIX)
def DoNothing():
    ###Exactly like the function says###
    return

