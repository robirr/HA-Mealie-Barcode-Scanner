import requests
import json

# TODO: Add caching of products so they can be looked up locally rather than hitting the API unless needed.
# TODO: If a UPCDB is configured, when a product isn't found in the OFF DB then try the UPCDB instead.
# TODO: Add a method to create a product in the OFF DB if not found anywhere.

@service(supports_response="only")
def barcode_lookup(barcode=0000000000000, return_response=True):
    """yaml
name: Barcode Lookup
description: Lookup a product barcode on the OpenFoodFacts API
fields:
    barcode:
        description: The product barcode to be looked up against the API.
        example: 5000147030156
        required: true
        selector:
            text:
    """
    # Build the URL for the OpenFoodFacts API call
    off_url = f'{pyscript.app_config["off_url_base"]}{barcode}.json'

    # Python dictionary to return data to Home Assistant
    dictionary = {}

    try:
        # Make the API request
        response = task.executor(requests.get, off_url) 
        # Raise an exception for HTTP errors
        response.raise_for_status()

        # Parse the JSON
        json_data = json.loads(response.text)

        # If the product is successfully returned from the API
        if json_data.get('status') == 1: # 1 = Product found
            dictionary['result'] = 'success'
            dictionary['barcode'] = barcode
            dictionary['brand'] = json_data.get('product').get('brands')
            dictionary['title'] = json_data.get('product').get('product_name')
            dictionary['type'] = json_data.get('product').get('product_type')
            dictionary['quantity'] = json_data.get('product').get('quantity')


            log.info(f"Barcode {barcode} identified as {dictionary['brand']} {dictionary['title']}")
            return dictionary
        # If the barcode is not in the database
        elif json_data.get('success') == 0: # 0 = Unknown product
            dictionary['result'] = 'unknown'
            dictionary['barcode'] = barcode
            log.info(f"Barcode {barcode} not found in OpenFoodFacts database")
            return dictionary
        # If an unknown error occurs
        else:
            dictionary['result'] = 'error'
            dictionary['error'] = response_text
            log.error(f"An error occurred while calling the OpenFoodFacts API: {response_text}")
            return dictionary

    # If a HTTP error occurs
    except requests.exceptions.RequestException as e:
        log.error(f"An error occurred while calling the OpenFoodFacts API: {e}")
        dictionary['result'] = 'error'
        dictionary['error'] = e
        return dictionary