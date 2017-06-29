base:
  'host.example.com':
    - one
    - two

  'role:webserver':
    - match: grain

  'first.example.com,second.example.com,third.example.com':
    - one
