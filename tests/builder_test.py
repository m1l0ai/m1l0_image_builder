from builder.service.imageservice import ImageBuilderService
from m1l0_services.imagebuilder.image_builder_pb2 import BuildRequest


def test_builder():
    service = ImageBuilderService()
    request = BuildRequest(id="123", source="dir:///tmp/test")
    resp = service.Build(request, None)
    print(resp)
    # for x in resp:
    #     print(x)