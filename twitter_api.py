import tweepy
from tweepy.errors import (
    BadRequest, Forbidden, HTTPException, NotFound, TooManyRequests,
    TweepyException, TwitterServerError, Unauthorized
)
from tweepy.models import Model
from urllib.parse import urlencode
import logging
import asyncio
import time
import sys
import os
from dotenv import load_dotenv

log = logging.getLogger(__name__)

# redefind tweepy API request method because we need to use asyncio instead of time.sleep

async def twpy_request(
    self, method, endpoint, *, endpoint_parameters=(), params=None,
    headers=None, json_payload=None, parser=None, payload_list=False,
    payload_type=None, post_data=None, files=None, require_auth=True,
    return_cursors=False, upload_api=False, use_cache=True, **kwargs
):
    # If authentication is required and no credentials
    # are provided, throw an error.
    if require_auth and not self.auth:
        raise TweepyException('Authentication required!')

    self.cached_result = False

    if headers is None:
        headers = {}
    headers["User-Agent"] = self.user_agent

    # Build the request URL
    path = f'/1.1/{endpoint}.json'
    if upload_api:
        url = 'https://' + self.upload_host + path
    else:
        url = 'https://' + self.host + path

    if params is None:
        params = {}
    for k, arg in kwargs.items():
        if arg is None:
            continue
        if k not in endpoint_parameters and k != "tweet_mode":
            log.warning(f'Unexpected parameter: {k}')
        params[k] = str(arg)
    log.debug("PARAMS: %r", params)

    # Query the cache if one is available
    # and this request uses a GET method.
    if use_cache and self.cache and method == 'GET':
        cache_result = self.cache.get(f'{path}?{urlencode(params)}')
        # if cache result found and not expired, return it
        if cache_result:
            # must restore api reference
            if isinstance(cache_result, list):
                for result in cache_result:
                    if isinstance(result, Model):
                        result._api = self
            else:
                if isinstance(cache_result, Model):
                    cache_result._api = self
            self.cached_result = True
            return cache_result

    # Monitoring rate limits
    remaining_calls = None
    reset_time = None

    if parser is None:
        parser = self.parser

    try:
        # Continue attempting request until successful
        # or maximum number of retries is reached.
        retries_performed = 0
        while retries_performed <= self.retry_count:
            if (self.wait_on_rate_limit and reset_time is not None
                and remaining_calls is not None
                and remaining_calls < 1):
                # Handle running out of API calls
                sleep_time = reset_time - int(time.time())
                if sleep_time > 0:
                    log.warning(f"Rate limit reached. Sleeping for: {sleep_time}")
                    # time.sleep(sleep_time + 1)  # Sleep for extra sec
                    await asyncio.sleep(sleep_time + 1)

            # Apply authentication
            auth = None
            if self.auth:
                auth = self.auth.apply_auth()

            # Execute request
            try:
                resp = self.session.request(
                    method, url, params=params, headers=headers,
                    data=post_data, files=files, json=json_payload,
                    timeout=self.timeout, auth=auth, proxies=self.proxy
                )
            except Exception as e:
                raise TweepyException(f'Failed to send request: {e}').with_traceback(sys.exc_info()[2])

            if 200 <= resp.status_code < 300:
                break

            rem_calls = resp.headers.get('x-rate-limit-remaining')
            if rem_calls is not None:
                remaining_calls = int(rem_calls)
            elif remaining_calls is not None:
                remaining_calls -= 1

            reset_time = resp.headers.get('x-rate-limit-reset')
            if reset_time is not None:
                reset_time = int(reset_time)

            retry_delay = self.retry_delay
            if resp.status_code in (420, 429) and self.wait_on_rate_limit:
                if remaining_calls == 0:
                    # If ran out of calls before waiting switching retry last call
                    continue
                if 'retry-after' in resp.headers:
                    retry_delay = float(resp.headers['retry-after'])
            elif self.retry_errors and resp.status_code not in self.retry_errors:
                # Exit request loop if non-retry error code
                break

            # Sleep before retrying request again
            # time.sleep(retry_delay)
            await asyncio.sleep(retry_delay)
            retries_performed += 1

        # If an error was returned, throw an exception
        self.last_response = resp
        if resp.status_code == 400:
            raise BadRequest(resp)
        if resp.status_code == 401:
            raise Unauthorized(resp)
        if resp.status_code == 403:
            raise Forbidden(resp)
        if resp.status_code == 404:
            raise NotFound(resp)
        if resp.status_code == 429:
            raise TooManyRequests(resp)
        if resp.status_code >= 500:
            raise TwitterServerError(resp)
        if resp.status_code and not 200 <= resp.status_code < 300:
            raise HTTPException(resp)

        # Parse the response payload
        return_cursors = return_cursors or 'cursor' in params or 'next' in params
        result = parser.parse(
            resp.text, api=self, payload_list=payload_list,
            payload_type=payload_type, return_cursors=return_cursors
        )

        # Store result into cache if one is available.
        if use_cache and self.cache and method == 'GET' and result:
            self.cache.store(f'{path}?{urlencode(params)}', result)

        return result
    finally:
        self.session.close()

tweepy.api.request = twpy_request

def _get_auth_keys():
    consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
    consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
    access_token_key = os.getenv('TWITTER_ACCESS_TOKEN_KEY')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    auth_keys = (
        consumer_key,
        consumer_secret,
        access_token_key,
        access_token_secret,
    )
    return auth_keys

def get_tweepy_api(consumer_key=None, consumer_secret=None, access_token_key=None, access_token_secret=None, wait_on_rate_limit=True):
    if not(all((consumer_key, consumer_secret, access_token_key, access_token_secret,))):
        (consumer_key, consumer_secret, access_token_key, access_token_secret,) = _get_auth_keys()
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token_key, access_token_secret)
    api = tweepy.API(auth, wait_on_rate_limit=wait_on_rate_limit)
    return api

async def get_user_name(id):
    api = get_tweepy_api()
    try:
        user = api.get_user(user_id=id)
    except Exception as err:
        print(err)
        return False
    return user.screen_name

async def get_followers_ids(screen_name):
    """
    https://dev.twitter.com/rest/reference/get/followers/ids

    Requests / 15-min window (app auth): 15
    """
    api = get_tweepy_api()
    ids = []
    is_first = True
    try:
        for page in tweepy.Cursor(api.get_friend_ids, screen_name=screen_name, count=5000).pages():
            print("In loop of get_followers_ids")
            if not is_first:
                # time.sleep(60)
                await asyncio.sleep(60)
            else:
                is_first = False
            ids.extend(page)
    except Exception as err:
        print(err)
    return ids
