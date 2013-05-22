"""Singleton for all of the library's communcation with the Earth Engine API."""



# Using lowercase function naming to match the JavaScript names.
# pylint: disable-msg=g-bad-name

import json
import urllib

import httplib2

import ee_exception


# OAuth2 credentials object.  This may be set by ee.Initialize().
_credentials = None

# The base URL for all data calls.  This is set by ee.initialize().
_api_base_url = None

# The base URL for map tiles.  This is set by ee.initialize().
_tile_base_url = None

# Whether the module has been initialized.
_initialized = False

# The default deadline.
DEFAULT_DEADLINE = 30

# The default base URL for API calls.
DEFAULT_API_BASE_URL = 'https://earthengine.googleapis.com/api'

# The default base URL for media/tile calls.
DEFAULT_TILE_BASE_URL = 'https://earthengine.googleapis.com/'


def initialize(credentials=None, api_base_url=None, tile_base_url=None):
  """Initializes the data module, setting credentials and base URLs.

  If any of the arguments are unspecified, they will keep their old values;
  the defaults if initialize() has never been called before.

  Args:
    credentials: The OAuth2 credentials.
    api_base_url: The EarthEngine REST API endpoint.
    tile_base_url: The EarthEngine REST tile endpoint.
  """
  global _api_base_url, _tile_base_url, _credentials, _initialized

  # If already initialized, only replace the explicitly specified parts.

  if credentials is not None:
    _credentials = credentials

  if api_base_url is not None:
    _api_base_url = api_base_url
  elif not _initialized:
    _api_base_url = DEFAULT_API_BASE_URL

  if tile_base_url is not None:
    _tile_base_url = tile_base_url
  elif not _initialized:
    _tile_base_url = DEFAULT_TILE_BASE_URL

  _initialized = True


def reset():
  """Resets the data module, clearing credentials and custom base URLs."""
  global _api_base_url, _tile_base_url, _credentials, _initialized
  _credentials = None
  _api_base_url = None
  _tile_base_url = None
  _initialized = False


def getInfo(asset_id):
  """Load info for an asset, given an asset id.

  Args:
    asset_id: The asset to be retrieved.

  Returns:
    The value call results.
  """
  return send_('/info', {'id': asset_id})


def getList(asset_id):
  """Get a list of contents for a collection asset.

  Args:
    asset_id: The collection to be examined.

  Returns:
    The list call results.
  """
  return send_('/list', {'asset_id': asset_id})


def getMapId(params):
  """Get a Map ID for a given asset.

  Args:
    params: An object containing visualization options with the
            following possible values:
      image - (JSON string) The image to render.
      version - (number) Version number of image (or latest).
      bands - (comma-seprated strings) Comma-delimited list of
          band names to be mapped to RGB.
      min - (comma-separated numbers) Value (or one per band)
          to map onto 00.
      max - (comma-separated numbers) Value (or one per band)
          to map onto FF.
      gain - (comma-separated numbers) Gain (or one per band)
          to map onto 00-FF.
      bias - (comma-separated numbers) Offset (or one per band)
          to map onto 00-FF.
      gamma - (comma-separated numbers) Gamma correction
          factor (or one per band)
      palette - (comma-separated strings) List of CSS-style color
          strings (single-band previews only).
      format (string) Either 'jpg' or 'png'.

  Returns:
    A dictionary containing "mapid" and "token" strings, which can
    be combined to retrieve tiles from the /map service.
  """
  params['json_format'] = 'v2'
  return send_('/mapid', params)


def getTileUrl(mapid, x, y, z):
  """Generate a URL for map tiles from a Map ID and coordinates.

  Args:
    mapid: The Map ID to generate tiles for, a dictionary containing "mapid"
        and "token" strings.
    x: The tile x coordinate.
    y: The tile y coordinate.
    z: The tile zoom level.

  Returns:
    The tile URL.
  """
  width = 2 ** z
  x %= width
  if x < 0:
    x += width
  return '%s/map/%s/%d/%d/%d?token=%s' % (
      _tile_base_url, mapid['mapid'], z, x, y, mapid['token'])


def getValue(params):
  """Retrieve a processed value from the front end.

  Args:
    params: A dictionary containing:
        json - (String) A JSON object to be evaluated.

  Returns:
    The value call results.
  """
  params['json_format'] = 'v2'
  return send_('/value', params)


def getThumbnail(params):
  """Get a Thumbnail for a given asset.

  Args:
    params: Parameters identical to getMapId, plus:
        size - (a number or pair of numbers in format WIDTHxHEIGHT) Maximum
          dimensions of the thumbnail to render, in pixels. If only one number
          is passed, it is used as the maximum, and the other dimension is
          computed by proportional scaling.
        region - (E,S,W,N or GeoJSON) Geospatial region of the image
          to render. By default, the whole image.
        format - (string) Either 'png' (default) or 'jpg'.

  Returns:
    A thumbnail image as raw PNG data.
  """
  return send_('/thumb', params, opt_method='GET', opt_raw=True)


def getThumbId(params):
  """Get a Thumbnail ID for a given asset.

  Args:
    params: Parameters identical to getMapId, plus:
        size - (a number or pair of numbers in format WIDTHxHEIGHT) Maximum
          dimensions of the thumbnail to render, in pixels. If only one number
          is passed, it is used as the maximum, and the other dimension is
          computed by proportional scaling.
        region - (E,S,W,N or GeoJSON) Geospatial region of the image
          to render. By default, the whole image.
        format - (string) Either 'png' (default) or 'jpg'.

  Returns:
    A thumbnail ID.
  """
  request = params.copy()
  request['getid'] = '1'
  request['json_format'] = 'v2'
  if 'size' in request and isinstance(request['size'], (list, tuple)):
    request['size'] = 'x'.join(map(str, request['size']))
  return send_('/thumb', request)


def makeThumbUrl(thumbId):
  """Create a thumbnail URL from the given thumbid and token.

  Args:
    thumbId: An object containing a thumbnail thumbid and token.

  Returns:
    A URL from which the thumbnail can be obtained.
  """
  return '%s/api/thumb?thumbid=%s&token=%s' % (
      _tile_base_url, thumbId['thumbid'], thumbId['token'])


def getDownloadId(params):
  """Get a Download ID.

  Args:
    params: An object containing visualization options with the following
      possible values:
        name - a base name to use when constructing filenames.
        bands - a description of the bands to download. Must be an array of
            dictionaries, each with the following keys:
          id - the name of the band, a string, required.
          crs - an optional CRS string defining the band projection.
          crs_transform - an optional array of 6 numbers specifying an affine
              transform from the specified CRS, in the order: xScale,
              yShearing, xShearing, yScale, xTranslation and yTranslation.
          dimensions - an optional array of two integers defining the width and
              height to which the band is cropped.
          scale - an optional number, specifying the scale in meters of the
                 band; ignored if crs and crs_transform is specified.
        crs - a default CRS string to use for any bands that do not explicitly
            specify one.
        crs_transform - a default affine transform to use for any bands that do
            not specify one, of the same format as the crs_transform of bands.
        dimensions - default image cropping dimensions to use for any bands
            that do not specify them.
        scale - a default scale to use for any bands that do not specify one;
            ignored if crs and crs_transform is specified.
        region - a polygon specifying a region to download; ignored if crs
            and crs_transform is specified.

  Returns:
    A dict containing a docid and token.
  """
  params['json_format'] = 'v2'
  return send_('/download', params)


def makeDownloadUrl(downloadId):
  """Create a download URL from the given docid and token.

  Args:
    downloadId: An object containing a download docid and token.

  Returns:
    A URL from which the download can be obtained.
  """
  return '%s/api/download?docid=%s&token=%s' % (
      _tile_base_url, downloadId['docid'], downloadId['token'])


def getAlgorithms():
  """Get the list of algorithms.

  Returns:
    The dictionary of algorithms.  Each algorithm is a dictionary containing
    the following fields:
        "description" - (string) A text description of the algorithm.
        "returns" - (string) The return type of the algorithm.
        "args" - An array of arguments.  Each argument specifies the following:
            "name" - (string) The name of the argument.
            "description" - (string) A text description of the argument.
            "type" - (string) The type of the argument.
            "optional" - (boolean) Whether the argument is optional or not.
            "default" - A representation of the default value if the argument
                is not specified.
  """
  return send_('/algorithms', {}, 'GET')


def createAsset(value, opt_path=None):
  """Save an asset.

  Args:
    value: The JSON-serialized value of the asset.
    opt_path: An optional desired ID, including full path.

  Returns:
    A description of the saved asset, including a generated ID.
  """
  args = {'value': value, 'json_format': 'v2'}
  if opt_path is not None:
    args['id'] = opt_path
  return send_('/create', args)


def send_(path, params, opt_method='POST', opt_raw=False):
  """Send an API call.

  Args:
    path: The API endpoint to call.
    params: The call parameters.
    opt_method: The HTTPRequest method (GET or POST).
    opt_raw: Whether the data should be returned raw, without attempting
        to decode it as JSON.

  Returns:
    The data object returned by the API call.

  Raises:
    EEException: For malformed requests or errors from the server.
  """
  # Make sure we never perform API calls before initialization.
  initialize()

  url = _api_base_url + path
  deadline = float(params.pop('deadline', DEFAULT_DEADLINE))
  payload = urllib.urlencode(params)
  http = httplib2.Http(timeout=deadline)

  headers = {}
  if _credentials:
    http = _credentials.authorize(http)

  if opt_method == 'GET':
    url = url + '?' + payload
    payload = None
  elif opt_method == 'POST':
    headers['Content-type'] = 'application/x-www-form-urlencoded'
  else:
    raise ee_exception.EEException('Unexpected request method: ' + opt_method)

  try:
    response, content = http.request(url, opt_method, payload, headers)
  except httplib2.HttpLib2Error, e:
    raise ee_exception.EEException(
        'Unexpected HTTP error: %s' % e.message)

  if response.status != 200:
    raise ee_exception.EEException('Server returned HTTP code: %d' %
                                   response.status)

  if opt_raw:
    return content
  else:
    content = json.loads(content)
    if 'error' in content:
      raise ee_exception.EEException(content['error'])
    if 'data' not in content:
      raise ee_exception.EEException('Missing data in response: ' + content)
    return content['data']
