Podcast2zim
=============

`podcast2zim` allows you to create a [ZIM file](https://openzim.org) from an RSS/Atom feed or Apple iTunes URL.

It downloads the podcast's audios, images, and other essential data and then produces JSON files. These JSON files are used by the UI (which is a Vuejs application that needs to be compiled as a static website with Vite and is then embedded inside the ZIM).

It uses [feedparser](https://feedparser.readthedocs.io/en/latest/) to parse RSS/Atom feeds. In the case an Apple iTunes URL is provided it resolves it to an RSS/Atom feed using Apple iTunes Lookup API and then passes it to the scraper. It is highly recommended that you try to get the RSS/Atom feed urls rather than resolving as it may return windowed versions of the podcast's RSS/Atom feeds. In one example a podcast that has over 2000 episodes returned a feed containing only ~50 episodes.

You can find any podcast's original RSS/Atom feed at [Listen Notes](https://www.listennotes.com/)

# Docker setup
```sh
docker build -t podcast2zim .
docker run --rm -t podcast2zim --help
```
You can then create a ZIM from the RSS/Atom feed like so:
```sh
docker run --rm -it -v "$(pwd)/output:/output" podcast2zim --feed-url "<your-rss-atom-feed-url>" --name "<name>" --output /output
```

# Local setup
Install hatch: 

```sh
pip3 install hatch
```

Build the ZIM UI first:

```sh
cd zimui && yarn install && yarn build
```

Start a hatch shell:

```sh
cd ..
mkdir -p output
cd scraper && hatch shell
podcast2zim --help
```
You can then create a ZIM from the RSS/Atom feed like so:
```sh
podcast2zim --feed-url "<rss-atom-feed-url>" --name "<name>"
```


# Credits

Default microphone artwork based on ['Mic 98' by instructure-ui](https://www.svgrepo.com/svg/501626/mic) (MIT License).

# License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0) or later, see [LICENSE](LICENSE) for more details.
