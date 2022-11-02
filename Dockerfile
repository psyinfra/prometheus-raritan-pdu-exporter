FROM python:3.8.15-bullseye

ADD . .

RUN pip3 install .

ENV LOG_LEVEL=WARNING
ENV PORT=:9950

CMD ["sh", "-c", "raritanpdu -c config.json --web.listen-address ${PORT} -l ${LOG_LEVEL}"]