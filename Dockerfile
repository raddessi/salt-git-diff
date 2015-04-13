FROM python:3-onbuild

RUN mkdir -p /mnt/git

WORKDIR /mnt/git

COPY salt-git-diff.py /usr/bin/salt-git-diff.py

VOLUME ["/mnt/git"]

ENTRYPOINT ["/usr/bin/salt-git-diff.py"]
