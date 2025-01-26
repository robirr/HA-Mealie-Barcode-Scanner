# Import python modules we need
import requests
import json
import csv

# FIXME: OFF returns a 404 code when the product isn't found. Because of this it never gets to try UPCDB.
# TODO: Adding a product adds it to the OpenFoodFacts and/or UPCDatabases also
# TODO: Test setting the upcdb_url_base and upcdb_api_key to blank in config stops it trying them for matches

################################################################################
# BARCODE LOOKUP - Available in HA
################################################################################
@service(supports_response="only") # Tells Pyscript to make this function available as a HA action
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
    product = {} # Python dictionary to return data to Home Assistant

    # Lookup in the cache first and if found, return that
    if not pyscript.app_config["cache_csv"] == None:
        # Lookup the barcode in the cache file
        cache = task.executor(cache_lookup, barcode, pyscript.app_config["cache_csv"])
        # If it is found in the cache then return it from the cache
        if cache['result'] == 'success':
            product['result'] = 'success'
            product['source'] = 'Cache'
            product['barcode'] = cache['barcode']
            product['brand'] = cache['brand']
            product['title'] = cache['product']
            product['type'] = cache['type']
            product['quantity'] = cache['qty']
            return product

        # Log if there was an error in the cache lookup
        if cache['result'] == 'error':
            product['result'] = 'error'
            product['source'] = 'Cache'
            product['error'] = cache['error']
            log.error(f"An error occurred while searching the cache: {product['error']}")
            return product

    # Lookup of OpenFoodFacts.org
    if not pyscript.app_config["off_url_base"] == None:
        try:
            # Build the URL for the OpenFoodFacts API call
            off_url = f'{pyscript.app_config["off_url_base"]}{barcode}.json'
        
            # Make the API request
            response = task.executor(requests.get, off_url) 
            # Raise an exception for HTTP errors
            response.raise_for_status()

            # Parse the JSON
            json_data = json.loads(response.text)

            # If the product is successfully returned from the API
            if json_data.get('status') == 1: # 1 = Product found
                # Populate the product from the OFF returned JSON
                product['result'] = 'success'
                product['source'] = 'OpenFoodFacts'
                product['barcode'] = barcode
                product['brand'] = json_data.get('product').get('brands').split(',')[0]
                product['title'] = json_data.get('product').get('product_name').replace(',', '')
                product['type'] = json_data.get('product').get('product_type').split(',')[0]
                product['quantity'] = json_data.get('product').get('quantity').split(',')[0]

                # Log the found product
                log.info(f"Barcode {barcode} identified as {product['brand']} {product['title']}")
                
                # Add it to the cache
                if not pyscript.app_config["cache_csv"] == None:
                    task.executor(cache_add, product, pyscript.app_config["cache_csv"])

                return product
            # If the barcode is not in the database
            elif json_data.get('success') == 0: # 0 = Unknown product
                product['result'] = 'unknown'
                product['source'] = 'OpenFoodFacts'
                product['barcode'] = barcode
                log.info(f"Barcode {barcode} not found in OpenFoodFacts database")
                return product
            # If an unknown error occurs
            else:
                product['result'] = 'error'
                product['source'] = 'OpenFoodFacts'
                product['error'] = response
                log.error(f"An error occurred while calling the OpenFoodFacts API: {product['error']}")
                return product

        # If a HTTP error occurs
        except requests.exceptions.RequestException as e:
            log.error(f"An error occurred while calling the OpenFoodFacts API: {e}")
            product['result'] = 'error'
            product['source'] = 'OpenFoodFacts'
            product['error'] = e
            return product

    if not pyscript.app_config["upcdb_url_base"] == None and not pyscript.app_config["upcdb_api_key"] == None:
        try:
            # Build the URL for the UPCDatabase API call
            upcdb_url = f'{pyscript.app_config["upcdb_url_base"]}{barcode}?apikey={pyscript.app_config["upcdb_api_key"]}'

            # Make the API request
            response = task.executor(requests.get, upcdb_url) 
            # Raise an exception for HTTP errors
            response.raise_for_status()

            # The UPCDatabase API sometimes returns a load of rubbish before the JSON. So we get rid of it.
            response_text = response.text
            json_start = response_text.find('{')
            response_clean = response_text[json_start:]

            # Parse the JSON
            json_data = json.loads(response_clean)

            # If the product is successfully returned from the API
            if json_data.get('success') == "true":
                # Populate the product from the UPCDatabase returned JSON
                product['result'] = 'success'
                product['source'] = 'UPCDatabase'
                product['barcode'] = barcode
                product['brand'] = json_data.get('brand').split(',')[0]
                if len(json_data.get('title')) >0:  
                    product['title'] = json_data.get('title').replace(',', '') 
                elif len(json_data.get('alias')) >0:
                    product['title'] = json_data.get('alias').replace(',', '') 
                else:
                    product['title'] = json_data.get('description').replace(',', '') 
                product['type'] = json_data.get('category').split(',')[0].lower()
                product['quantity'] = json_data.get('metadata').get('quantity').split(',')[0]

                # Log the found product
                log.info(f"Barcode {barcode} identified as {product['brand']} {product['title']}")
                
                # Add it to the cache
                if not pyscript.app_config["cache_csv"] == None:
                    task.executor(cache_add, product, pyscript.app_config["cache_csv"])

                return product
            # If the barcode is not in the database0
            elif json_data.get('success') == "false":
                product['result'] = 'unknown'
                product['source'] = 'UPCDatabase'
                product['barcode'] = barcode
                log.info(f"Barcode {barcode} not found in UPCDatabase database")
                return product
            # If an unknown error occurs
            else:
                product['result'] = 'error'
                product['source'] = 'UPCDatabase'
                product['error'] = response
                log.error(f"An error occurred while calling the UPCDatabase API: {product['error']}")
                return product

        except:
            log.error(f"An error occurred while calling the UPCDatabase API: {e}")
            product['result'] = 'error'
            product['source'] = 'UPCDatabase'
            product['error'] = e
            return product

################################################################################
# ADD PRODUCT TO THE CACHE
################################################################################
# We need the function to be compiled to access the open() function but it then 
# can't access the Pyscript app config. So we create a wrapper function which 
# can be called from Home Assistant which then calls the compiled function.
@service(supports_response="only") # Tells Pyscript to make this function available as a HA action
def barcode_cache_add(barcode, title, brand="", type="other", quantity="", return_response=True):
    """yaml
name: Barcode Cache Add
description: Adds a product to the local cache of barcodes that have either been returned from wesites or manually entered.
fields:
    barcode:
        description: The product barcode. Normally a 13 digit number but can also be other lengths.
        example: 5000147030156
        required: true
        selector:
            text:
    brand:
        description: The brand of the product.
        example: Robinsons
        required: false
        selector:
            text:
    title:
        description: The name of the of the product.
        example: Summer Fruits Squash
        required: true
        selector:
            text:
    type:
        description: The type of product. Currently supported values are "food" and "other".
        example: food
        required: true
        selector:
            select:
                options:
                    - food
                    - other
    quantity:
        description: The quantity, weight, or measurement the product comes in.
        example: 1.5l
        required: true
        selector:
            text:
    """
    # Create a dictionary for the product
    product = {}
    product["barcode"] = barcode
    product["brand"] = brand
    product["title"] = title
    product["type"] = type
    product["quantity"] = quantity

    # Call the compiled function that can access the file with open()
    result = task.executor(cache_add, product, pyscript.app_config["cache_csv"])
    return {"result": "success"} if result == True else {"result": "failed"}

@pyscript_compile # Tells Pyscript to compile the function
def cache_add(product, file):

    # Sort the passed product object into a row ready for the csv to make sure it is in the correct order etc
    row = [product['barcode'], product['brand'], product['title'], product['type'], product['quantity']]

    # Open the cache csv in append mode and create a file object
    with open(file, 'a') as cache_f_obj:
        cache_w_obj = csv.writer(cache_f_obj) # Pass the file object to csv.writer() to get a writer object
        cache_w_obj.writerow(row) # Add the row to the writer object
        cache_f_obj.close # Close the file object

        return True
    return False

################################################################################
# CACHE LOOKUP
################################################################################
@pyscript_compile
def cache_lookup(barcode, file):
    product = {} # Dictionary to pass back

    try:
        with open(file, 'r') as cache_f_obj: # Open the cache file in read mode
            for row in csv.reader(cache_f_obj): # Loop through the rows
                if row[0] == str(barcode): # If the row matches the barcode
                    # Fill out the dictionary to returm
                    product['result'] = 'success'
                    product['barcode'] = barcode
                    product['brand'] = row[1]
                    product['product'] = row[2]
                    product['type'] = row[3]
                    product['qty'] = row[4]
                    cache_f_obj.close # Close the file
                    return product

            # If the barcode isn't found in the file return unknown
            product['result'] = 'unknown'
            product['barcode'] = barcode
            cache_f_obj.close # Close the file
            return product
            
    except requests.exceptions.RequestException as e: # If an error occured return it
        product['result'] = 'error'
        product['error'] = e
        return product

################################################################################
# CLEAR THE CACHE
################################################################################
# We need the function to be compiled to access the open() function but it then 
# can't access the Pyscript app config. So we create a wrapper function which 
# can be called from Home Assistant which then calls the compiled function.
@service(supports_response="only") # Tells Pyscript to make this function available as a HA action
def barcode_cache_clear(return_response=True):
    """yaml
name: Barcode Cache Clear
description: WARNING THIS CAN'T BE UNDONE! Clears the local cache of barcodes that have either been returned from wesites or manually entered.
    """
    # Call the compiled function that can access the file with open()
    result = task.executor(cache_clear, pyscript.app_config["cache_csv"])
    return result

@pyscript_compile
def cache_clear(file):
    result = {} # Dictionary to pass back

    # Clear the csv file
    with open(file, 'w+') as cache_f_obj: # w+ opens the file in write mode but truncates the file
        # Recreate the header row
        header_row = ['barcode', 'brand', 'product', 'type', 'qty']
        # Pass the file object to csv.writer() to get a writer object
        cache_w_obj = csv.writer(cache_f_obj)
        # Add the row to the writer object
        cache_w_obj.writerow(header_row)
        # Close the file
        cache_f_obj.close()

        result['result'] = 'success'
        return result