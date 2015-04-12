# Salt git diff
See which hosts in top file were affected by latest git commit

# Usage
Navigate to your salt states or pillars location and run:

    docker run -i -v $(pwd):/mnt/git tomologic/salt-git-diff

Default output format is YAML. You can get JSON instead:

    docker run -i -v $(pwd):/mnt/git tomologic/salt-git-diff --json

# Output
YAML format:

    - '*'
    - host2.example.com
    - host3.example.com
    - '*.subdomain.example.com'

JSON format:

    [
        "*",
        "host2.example.com",
        "host3.example.com",
        "*.subdomain.example.com"
    ]
    
# Limitations
* Skips any selector with ":" in it in top file, like "os:CentOS"
