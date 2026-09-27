import { io } from 'socket.io-client'
import { getCachedListResource, getCachedResource } from 'frappe-ui'

export function initSocket() {
  let siteName = window.site_name
  let url

  if (import.meta.env.DEV) {
    // Dev: Vite serves the app on its own port while the realtime worker runs
    // separately, so talk to it directly.
    let socketio_port = window.socketio_port || 9000
    url = `${window.location.protocol}//${window.location.hostname}:${socketio_port}/${siteName}`
  } else {
    // Prod: same origin. The reverse proxy in front of us forwards /socket.io/
    // to the realtime worker, which keeps this working over plain HTTP, over
    // HTTPS, and on non-standard ports (two stacks on 8081/8082) alike.
    // Deriving the scheme from the port -- as this used to -- forced https://
    // whenever the URL had no explicit port, breaking realtime on plain-HTTP
    // deployments behind port 80.
    url = `${window.location.origin}/${siteName}`
  }

  let socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  socket.on('refetch_resource', (data) => {
    if (data.cache_key) {
      let resource =
        getCachedResource(data.cache_key) ||
        getCachedListResource(data.cache_key)
      if (resource) {
        resource.reload()
      }
    }
  })
  return socket
}
