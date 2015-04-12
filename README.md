# Salt git diff
See which hosts in top file were affected by latest git commit

# Usage
Navigate to your salt states or pillars location and run:

    docker run -i -v $(pwd):/mnt/git tomologic/salt-git-diff

# Output
YAML format:

    added: []
    changed:
      - host1.example.com:
        added:
          - nginx
        removed:
          - apache
    removed: []
    unchanged:
      - '*'
      - host2.example.com
      - host3.example.com
      - '*.subdomain.example.com'

# Limitations
* Only looks at top file difference
