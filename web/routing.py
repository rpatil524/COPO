from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import web.apps.web_copo.routing

application = ProtocolTypeRouter({
    'websocket': SessionMiddlewareStack(
        AuthMiddlewareStack(

            URLRouter(
                web.apps.web_copo.routing.websocket_urlpatterns
            )
        ),
    )
})
