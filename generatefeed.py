from feedgen.feed import FeedGenerator
from os import listdir
from os.path import isfile, join
import pathlib

server_path = "http://apps.breakall.org:65123/"


fg = FeedGenerator()
fg.load_extension('podcast')
fg.podcast.itunes_category('News')

fg.link(href=server_path + "rss.xml", rel='self')
fg.title('shiftFM')
fg.description('Time-shifted FM radio programs') 



files = [f for f in listdir(pathlib.Path(__file__).parent.resolve()) if isfile(join(pathlib.Path(__file__).parent.resolve(), f))]

for f in files:
	if 'mp3' in f:
		fe = fg.add_entry()
		fe.id(f)
		fe.title(f)
		fe.enclosure(server_path + f, 0, 'audio/mpeg')

fg.rss_str(pretty=True)
fg.rss_file('rss.xml')
