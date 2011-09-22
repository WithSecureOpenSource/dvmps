from wsgiref.simple_server import make_server
import VMAllocationService
import json

vma = None

def vm_allocator_app(environ, start_response):
    command = environ['PATH_INFO']

    status = '200 OK'
    headers = [('Content-type', 'text/plain')]

    start_response(status, headers)

    res = None
    request_params = None

    if vma is not None and environ['REQUEST_METHOD'] == 'POST' and environ.has_key('CONTENT_LENGTH'):
        data_size = int(environ['CONTENT_LENGTH'])
        data = environ['wsgi.input'].read(data_size)
        request_params = json.loads(data)

        if command == '/allocate':
            base_image = None
            expires = None
            comment = None
            if request_params.has_key('base_image'):
                base_image = request_params['base_image']
            if request_params.has_key('expires'):
                expires = request_params['expires']
            if request_params.has_key('comment'):
                comment = request_params['comment']
            if base_image is not None and expires is not None:
                res = vma.allocate_image(base_image, expires, comment)
        elif command == '/deallocate':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = vma.deallocate_image(image_id)
        elif command == '/revert':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = vma.revert_image(image_id)
        elif command == '/poweroff':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = vma.poweroff_image(image_id)
        elif command == '/poweron':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = vma.poweron_image(image_id)
        elif command == '/status':
            image_id = None
            if request_params.has_key('image_id'):
                image_id = request_params['image_id']
            if image_id is not None:
                res = vma.image_status(image_id)
        elif command == '/systemstatus':
            res = vma.status()

    return [json.dumps(res)]

if __name__ == '__main__':
    vma = VMAllocationService.VMAllocationService(database='dvmps')

    httpd = make_server('', 80, vm_allocator_app)
    print "Serving on port 80..."

    # Serve until process is killed
    httpd.serve_forever()
