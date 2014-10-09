import time, datetime
import hmac, hashlib
import urllib, urllib2, socket
import json

"""SERPmetrics Python-SDK"""
class SMapi(object):
    VERSION = 'v0.0.1'

    api_url = 'http://api.serpmetrics.com'
    user_agent = 'SERPmetrics Python Library'
    retries = 3

    _http_status = None
    _credentials = {'key':None, 'secret':None}

    """
    Sets up a new SM instance

    @param dict credentials
    @return void
    """
    def __init__(self, credentials={}):
        super(SMapi, self).__init__()
        self._credentials = credentials

    """
    Adds a new keyword to the queue. engines should be passed as a list
    of {engine}_{locale} strings.

        Also takes a list of keyword strings

    Ex. ["google_en-us", "yahoo_en-us", "bing_en-us"]

    @param string or list keyword
    @param list engines
    @return mixed
    """
    def add(self, keyword, engines):
    	if not isinstance(engines, list) and len(engines):
    		engines = [engines]
        options = {'path':'/keywords/add', 'params':{'keyword':keyword, 'engines':engines}}
        return self.rest(options)

    """
    Removes a keyword from the queue.
    Note: this REMOVES a keyword entirely, including ALL engines assigned. To update
            a keywords engine list, simply call add() with the new engine list

            Also takes a list of keyword_id strings.

    @param string or list keyword_id
    @return mixed
    """
    def remove(self, keyword_id):
        options = {'path':'/keywords/delete', 'params':{'keyword_id':keyword_id}}
        return self.rest(options)

    """
    Adds a new keyword to the priority queue, usage as per add()
    """
    def priority_add(self, keyword, engines):
        if not isinstance(engines, list) and len(engines):
            engines = [engines]
        options = {'path':'/priority/add', 'params':{'keyword':keyword, 'engines':engines}}
        return self.rest(options)

    """
    Gets status for a given priority_id

    @param string priority_id
    @return mixed
    """
    def priority_status(self, priority_id):
        options = {'path':'/priority/status', 'params':{'priority_id':priority_id}}
        return self.rest(options)

    """
    Gets last limit SERP check timestamps/ids for keyword/engine combination. engine
    should be in the format {engine}_{locale} (for example google_en-us).

    @param string keyword_id
    @param string engine
    @param integer limit (optional)
    @return dict
    """
    def check(self, keyword_id, engine, limit=10):
        options = {'path':'/keywords/check', 'params':{'keyword_id':keyword_id, 'engine':engine, 'limit':limit}, 'method':'GET'}
        return self.rest(options)

    """
    Get SERP data for given id. Restricted to optional specified domain

    @param string id
    @param string domain
    @return mixed
    """
    def serp(self, check_id, domain=None):
        options = {'path':'/keywords/serp', 'params':{'check_id':check_id, 'domain':domain}}
        return self.rest(options)

    """
    Get current credit balance

    @return mixed
    """
    def credit(self):
        options = {'path':'/users/credit'}
        return self.rest(options)

    """
    Get trended flux data for a given engine_code

    @param string engine_code
    @param string type
    @return mixed
    """
    def flux(self, engine_code, _type='daily'):
        options = {'path':'/flux/trend', 'params':{'engine_code':engine_code, 'type':_type}}
        return self.rest(options)

    """
    Generates authentication signature

    @param dict credentials
    @return dict
    """
    def _generate_signature(self, credentials=None):
        now = datetime.datetime.now()
        ts  = str(time.mktime(now.timetuple())).split('.')[0]

        if not credentials or not len(credentials):
            credentials = self.credentials

        h = hmac.new(credentials['secret'], ts, hashlib.sha256).digest()
        signature = h.encode("base64")
        #signature = ts+signature

        return {'ts':int(ts), 'signature':signature}

    """
    Generates a REST request to the API with retries and exponential backoff

    @param dict options
    @param dict credentials
    @return mixed
    """
    def rest(self, options, credentials={}):
        defaults = {'method':'POST',
                                'url':self.api_url,
                                'path':'/', }

        # Concatenate options with defaults
        for key in defaults.keys():
            if not key in options.keys():
                options[key] = defaults[key]

        if 'params' in options.keys() and options['params']:
            params = json.dumps(options['params'])
        else:
            params = {}

        if not credentials:
            credentials = self._credentials

        auth = self._generate_signature(credentials)
        auth['signature'] = auth['signature'].strip('\n')

        _params = params if params else None

        options['query'] = {'key':credentials['key'],
                            'auth':auth['signature'],
                            'ts':auth['ts'],
                            'params': _params }

        url = options['url'] + options['path']

        req_vals = {'params':options['query']['params'],
                                'key':options['query']['key'],
                                'auth':options['query']['auth'],
                                'ts':options['query']['ts'] }

        req_data = urllib.urlencode(req_vals)

        if options['method'] == 'GET':
        	url = url + '?' + req_data
        	req = urllib2.Request(url)
        else:
        	req = urllib2.Request(url, req_data)
        req.add_header('User-Agent', self.user_agent+' '+self.VERSION)

        attempt = 0
        while True:
            attempt += 1
            try:
                res = urllib2.urlopen(req)
                
                self._http_status = res.getcode()
                res_data = res.read()
                json_data = json.loads(res_data)
                return json.loads(json.dumps(json_data))
            except urllib2.URLError, e:
                if hasattr(e, "reason") and isinstance(e.reason, socket.timeout):
                	if not self._exponential_backoff(attempt, self.retries):
                		return False
                else:
                    self._http_status = e.code
                    break
            finally:
                pass


    """
    Return the last HTTP status code received. Useful for debugging purposes.

    @return integer
    """
    def http_status(self):
        return self._http_status

    """
    Implements exponential backoff

    @param integer current
    @param integer max
    @return bool
    """
    def _exponential_backoff(self, current, _max):
        if current <= _max:
            delay = int((2 ** current) * 100000)
            time.sleep(delay)
            return True

        return False
