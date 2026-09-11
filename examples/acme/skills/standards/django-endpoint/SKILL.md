---
name: implement-endpoint
class: implement/endpoint
id: "@acme/django-endpoint"
version: 1.0.0
description: Implement an endpoint from its API-* contract: schemas, thin controller, error mapping, auth, OpenAPI sync; use on "add endpoint/route/API/handler" or controller changes.
---
# @acme/django-endpoint

ACME endpoints are Django REST Framework views over services.
1. Serializer from the API-* contract (field names from the dictionary); validation in the serializer only.
2. View ≤ 20 lines: permission class, serializer, one service call, response; errors mapped in one handler module.
3. Service owns the transaction and the authorisation check; never the view.
4. OpenAPI regenerated (`drf-spectacular`); `@implements API-…`; contract test for the endpoint.
