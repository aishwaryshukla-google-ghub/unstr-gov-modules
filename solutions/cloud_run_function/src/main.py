import functions_framework
from flask import jsonify

@functions_framework.http
def hello_world(request):
    """HTTP Cloud Run Function entry point.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and "name" in request_json:
        name = request_json["name"]
    elif request_args and "name" in request_args:
        name = request_args["name"]
    else:
        name = "World"

    return jsonify({
        "status": "success",
        "message": f"Hello, {name}! Cloud Run Function deployed successfully via Terraform module.",
        "service": "NYL Unstructured Governance Cloud Run Function"
    })
