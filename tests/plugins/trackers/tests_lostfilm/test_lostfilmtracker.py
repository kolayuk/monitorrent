# coding=utf-8
import pytest
import requests_mock
from ddt import ddt, data, unpack
from future.utils import PY3
from monitorrent.plugins.trackers import TrackerSettings
from monitorrent.plugins.trackers.lostfilm import LostFilmTVTracker, LostFilmTVLoginFailedException
from unittest import TestCase
from tests import use_vcr, ReadContentMixin
from tests.plugins.trackers.tests_lostfilm.lostfilmtracker_helper import LostFilmTrackerHelper

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# For real testing you can create LostFilmTrackerHelper over login method,
# and remove all corresponding cassettes.
# ex.: helper = LostFilmTrackerHelper.login("login", "password", "uid")
# note: uid can be found on page: http://www.lostfilm.tv/my_settings
# field Мой ID: <id>
helper = LostFilmTrackerHelper()


@ddt
class LostFilmTrackerTest(ReadContentMixin, TestCase):
    def setUp(self):
        self.tracker_settings = TrackerSettings(10, None)
        self.tracker = LostFilmTVTracker()
        self.tracker.tracker_settings = self.tracker_settings
        super(LostFilmTrackerTest, self).setUp()

    @helper.use_vcr()
    def test_login(self):
        self.tracker.login(helper.real_email, helper.real_password)
        assert self.tracker.session is not None

    @use_vcr()
    def test_fail_login(self):
        with self.assertRaises(LostFilmTVLoginFailedException) as cm:
            self.tracker.login("admin", "FAKE_PASSWORD")
        assert cm.exception.code == 3

    @helper.use_vcr()
    def test_verify_success(self):
        tracker = LostFilmTVTracker(helper.real_session)
        tracker.tracker_settings = self.tracker_settings
        assert tracker.verify()

    def test_verify_false(self):
        assert not self.tracker.verify()

    @use_vcr()
    def test_verify_fail(self):
        tracker = LostFilmTVTracker("1234567890abcdefghjklmnopqrstuvuywxyz")
        tracker.tracker_settings = self.tracker_settings
        assert not tracker.verify()

    @data(('http://www.lostfilm.tv/series/12_Monkeys/seasons', True),
          ('http://www.lostfilm.tv/series/12_Monkeys/bombolaya', True),
          ('http://www.lostfilm.tv/series/12_Monkeys', True),
          ('http://www.lostfilm.tv/my.php', False))
    @unpack
    def test_can_parse_url(self, url, value):
        assert self.tracker.can_parse_url(url) == value

    @use_vcr()
    def test_parse_correct_url_success(self):
        title = self.tracker.parse_url('http://www.lostfilm.tv/series/12_Monkeys')
        assert title['name'] == u'12 обезьян'
        assert title['original_name'] == u'12 Monkeys'

    @use_vcr()
    def test_parse_https_url_success(self):
        title = self.tracker.parse_url('https://www.lostfilm.tv/series/12_Monkeys')
        assert title['original_name'] == u'12 Monkeys'

    @use_vcr()
    def test_parse_correct_url_issue_22_1(self):
        title = self.tracker.parse_url('http://www.lostfilm.tv/series/The_Vampire_Diaries')
        assert title['name'] == u'Дневники вампира'
        assert title['original_name'] == u'The Vampire Diaries'

    @use_vcr()
    def test_parse_correct_url_issue_22_2(self):
        title = self.tracker.parse_url('http://www.lostfilm.tv/series/Grimm')
        assert title['name'] == u'Гримм'
        assert title['original_name'] == u'Grimm'

    @use_vcr()
    def test_parse_incorrect_url_1(self):
        url = 'http://www.lostfilm.tv/not_a_series/SuperSeries'
        self.assertIsNone(self.tracker.parse_url(url))

    @use_vcr()
    def test_parse_incorrect_url_2(self):
        url = 'http://www.lostfilm.tv/browse.php?cat=2'
        resp = self.tracker.parse_url(url)
        self.assertIsNotNone(resp)
        self.assertNotEqual(resp.status_code, 200)

    @use_vcr()
    def test_parse_series_success(self):
        url = 'http://www.lostfilm.tv/series/Grimm/seasons'
        parsed_url = self.tracker.parse_url(url, True)
        assert parsed_url['cat'] == 160
        assert parsed_url['show_url_fragment'] == 'Grimm'
        assert parsed_url['name'] == u'Гримм'
        assert parsed_url['original_name'] == u'Grimm'
        assert len(parsed_url['seasons']) == 6
        assert len(parsed_url['seasons'][6]['episodes']) == 4
        assert len(parsed_url['seasons'][5]['episodes']) == 22
        assert len(parsed_url['seasons'][4]['episodes']) == 22
        assert len(parsed_url['seasons'][3]['episodes']) == 22
        assert len(parsed_url['seasons'][2]['episodes']) == 22
        assert len(parsed_url['seasons'][1]['episodes']) == 22

    @use_vcr()
    def test_parse_series_success_2(self):
        url = 'http://www.lostfilm.tv/series/Sherlock/seasons'
        parsed_url = self.tracker.parse_url(url, True)
        assert parsed_url['cat'] == 130
        assert parsed_url['show_url_fragment'] == 'Sherlock'
        assert parsed_url['name'] == u'Шерлок'
        assert parsed_url['original_name'] == u'Sherlock'
        assert len(parsed_url['seasons']) == 5
        assert len(parsed_url['seasons'][4]['episodes']) == 3
        assert len(parsed_url['seasons'][3]['episodes']) == 3
        assert len(parsed_url['seasons'][2]['episodes']) == 3
        assert len(parsed_url['seasons'][1]['episodes']) == 3
        assert len(parsed_url['seasons']['additional']['episodes']) == 1

    @use_vcr()
    def test_parse_series_success_3(self):
        url = 'http://www.lostfilm.tv/series/Castle/seasons'
        parsed_url = self.tracker.parse_url(url, True)
        assert parsed_url['cat'] == 129
        assert parsed_url['name'] == u'Касл'
        assert parsed_url['original_name'] == u'Castle'
        assert len(parsed_url['seasons']) == 8
        assert len(parsed_url['seasons'][8]['episodes']) == 22
        assert len(parsed_url['seasons'][7]['episodes']) == 23
        assert len(parsed_url['seasons'][6]['episodes']) == 23
        assert len(parsed_url['seasons'][5]['episodes']) == 24
        assert len(parsed_url['seasons'][4]['episodes']) == 23
        assert len(parsed_url['seasons'][3]['episodes']) == 24
        assert len(parsed_url['seasons'][2]['episodes']) == 24
        assert len(parsed_url['seasons'][1]['episodes']) == 10

    @use_vcr()
    def test_parse_series_with_multiple_episodes_in_one_file(self):
        url = 'http://www.lostfilm.tv/series/Under_the_Dome/seasons'
        parsed_url = self.tracker.parse_url(url, True)
        assert parsed_url['cat'] == 186
        assert parsed_url['name'] == u'Под куполом'
        assert parsed_url['original_name'] == u'Under the Dome'
        assert len(parsed_url['seasons']) == 3
        assert len(parsed_url['seasons'][3]['episodes']) == 13
        assert len(parsed_url['seasons'][2]['episodes']) == 13
        assert len(parsed_url['seasons'][1]['episodes']) == 13

    @use_vcr()
    def test_parse_series_with_intermediate_seasons(self):
        url = 'http://www.lostfilm.tv/series/Farscape/seasons'
        parsed_url = self.tracker.parse_url(url, True)
        assert parsed_url['cat'] == 40
        assert len(parsed_url['seasons']) == 4
        # assert len(parsed_url['special_episodes']) == 1
        # assert parsed_url['special_episodes'][0]['season_info']) == (4, 5, 2)

    @use_vcr()
    def test_parse_series_special_serires_1(self):
        url = 'http://www.lostfilm.tv/browse.php?cat=112'
        parsed_url = self.tracker.parse_url(url, True)
        self.assertEqual(112, parsed_url['cat'])
        self.assertEqual(30, len(parsed_url['episodes']))
        self.assertEqual(3, len(parsed_url['complete_seasons']))

    @helper.use_vcr()
    def test_download_info(self):
        url = 'http://www.lostfilm.tv/series/Grimm/seasons'
        tracker = LostFilmTVTracker(helper.real_uid, helper.real_pass, helper.real_usess)
        tracker.tracker_settings = self.tracker_settings
        downloads = tracker.get_download_info(url, 4, 22)

        self.assertEqual(3, len(downloads))
        if PY3:
            # Python 3.4+
            self.assertCountEqual(['SD', '720p', '1080p'], [d['quality'] for d in downloads])
        else:
            # Python 2.7
            self.assertItemsEqual(['SD', '720p', '1080p'], [d['quality'] for d in downloads])

    @helper.use_vcr()
    def test_download_info_2(self):
        url = 'http://www.lostfilm.tv/browse.php?cat=37'
        tracker = LostFilmTVTracker(helper.real_uid, helper.real_pass, helper.real_usess)
        tracker.tracker_settings = self.tracker_settings
        downloads_4_9 = tracker.get_download_info(url, 4, 9)

        self.assertEqual(1, len(downloads_4_9))
        self.assertEqual('SD', downloads_4_9[0]['quality'])

        downloads_4_10 = tracker.get_download_info(url, 4, 10)

        self.assertEqual(2, len(downloads_4_10))
        if PY3:
            self.assertCountEqual(['SD', '720p'], [d['quality'] for d in downloads_4_10])
        else:
            self.assertItemsEqual(['SD', '720p'], [d['quality'] for d in downloads_4_10])

    def test_download_info_3(self):
        url = 'http://www.lostfilm.tv/browse_wrong.php?cat=2'
        tracker = LostFilmTVTracker(helper.real_uid, helper.real_pass, helper.real_usess)
        tracker.tracker_settings = self.tracker_settings
        self.assertIsNone(tracker.get_download_info(url, 4, 9))

    def test_parse_corrent_rss_title0(self):
        t1 = u'Мистер Робот (Mr. Robot). уя3вим0сти.wmv (3xpl0its.wmv) [MP4]. (S01E05)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Мистер Робот', parsed['name'])
        self.assertEqual(u'Mr. Robot', parsed['original_name'])
        self.assertEqual(u'уя3вим0сти.wmv', parsed['title'])
        self.assertEqual(u'3xpl0its.wmv', parsed['original_title'])
        self.assertEqual(u'720p', parsed['quality'])
        self.assertEqual(u'S01E05', parsed['episode_info'])
        self.assertEqual(1, parsed['season'])
        self.assertEqual(5, parsed['episode'])

    def test_parse_corrent_rss_title1(self):
        t1 = u'Мистер Робот (Mr. Robot). уя3вим0сти.wmv (3xpl0its.wmv). (S01E05)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Мистер Робот', parsed['name'])
        self.assertEqual(u'Mr. Robot', parsed['original_name'])
        self.assertEqual(u'уя3вим0сти.wmv', parsed['title'])
        self.assertEqual(u'3xpl0its.wmv', parsed['original_title'])
        self.assertEqual(u'SD', parsed['quality'])
        self.assertEqual(u'S01E05', parsed['episode_info'])
        self.assertEqual(1, parsed['season'])
        self.assertEqual(5, parsed['episode'])

    @data(u'Мистер Робот (Mr. Robot. уя3вим0сти.wmv (3xpl0its.wmv). (S01E05)',
          u'Мистер Робот (Mr. Robot). уя3вим0сти.wmv (3xpl0its.wmv). (S01E)')
    def test_parse_incorrent_rss_title1(self, title):
        self.assertIsNone(LostFilmTVTracker.parse_rss_title(title))

    def test_parse_special_rss_title(self):
        t1 = u'Под куполом (Under the Dome). Идите дальше/А я останусь (Move On/But I\'m Not) [1080p]. (S03E01E02)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Под куполом', parsed['name'])
        self.assertEqual(u'Under the Dome', parsed['original_name'])
        self.assertEqual(u'Идите дальше/А я останусь', parsed['title'])
        self.assertEqual(u'Move On/But I\'m Not', parsed['original_title'])
        self.assertEqual(u'1080p', parsed['quality'])
        self.assertEqual(u'S03E01E02', parsed['episode_info'])
        self.assertEqual(3, parsed['season'])
        self.assertEqual(2, parsed['episode'])

    def test_parse_special_rss_title2(self):
        t1 = u'Люди (Humans). Эпизод 8 [MP4]. (S01E08)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Люди', parsed['name'])
        self.assertEqual(u'Humans', parsed['original_name'])
        self.assertEqual(u'Эпизод 8', parsed['title'])
        self.assertIsNone(parsed['original_title'])
        self.assertEqual(u'720p', parsed['quality'])
        self.assertEqual(u'S01E08', parsed['episode_info'])
        self.assertEqual(1, parsed['season'])
        self.assertEqual(8, parsed['episode'])

    def test_parse_special_rss_title3(self):
        t1 = u'Люди (Humans). Эпизод 8. (S01E08)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Люди', parsed['name'])
        self.assertEqual(u'Humans', parsed['original_name'])
        self.assertEqual(u'Эпизод 8', parsed['title'])
        self.assertIsNone(parsed['original_title'])
        self.assertEqual(u'SD', parsed['quality'])
        self.assertEqual(u'S01E08', parsed['episode_info'])
        self.assertEqual(1, parsed['season'])
        self.assertEqual(8, parsed['episode'])

    def test_parse_special_rss_title4(self):
        t1 = u'Люди (Humans). Эпизод 8 [WEBRip]. (S01E08)'
        parsed = LostFilmTVTracker.parse_rss_title(t1)
        self.assertEqual(u'Люди', parsed['name'])
        self.assertEqual(u'Humans', parsed['original_name'])
        self.assertEqual(u'Эпизод 8', parsed['title'])
        self.assertIsNone(parsed['original_title'])
        self.assertEqual(u'unknown', parsed['quality'])
        self.assertEqual(u'S01E08', parsed['episode_info'])
        self.assertEqual(1, parsed['season'])
        self.assertEqual(8, parsed['episode'])

    @requests_mock.Mocker()
    def test_httpretty_login_success(self, mocker):
        """
        :type mocker: requests_mock.Mocker
        """
        uid = u'151548'
        pass_ = u'dd770c2445d297ed0aa192c153e5424c'
        usess = u'e76e71e0f32e65c2470e42016dbb785e'

        mocker.post('https://login1.bogi.ru/login.php?referer=https%3A%2F%2Fwww.lostfilm.tv%2F',
                    text=self.read_httpretty_content(u'test_lostfilmtracker.1.login1.bogi.ru.html',
                                                     encoding='utf-8'))

        mocker.post(u'http://www.lostfilm.tv/blg.php?ref=random',
                    text='', status_code=302,
                    cookies={
                        u"uid": uid,
                        u"pass": pass_
                    },
                    headers={'location': u'/'})
        mocker.get(u'http://www.lostfilm.tv/my.php', text=u'(usess={})'.format(usess))

        self.tracker.login(u'fakelogin', u'p@$$w0rd')

        self.assertEqual(self.tracker.c_uid, uid)
        self.assertEqual(self.tracker.c_pass, pass_)
        self.assertEqual(self.tracker.c_usess, usess)

    @requests_mock.Mocker()
    def test_httpretty_unknown_login_failed(self, mocker):
        """
        :type mocker: requests_mock.Mocker
        """
        mocker.register_uri(requests_mock.POST,
                            u'https://login1.bogi.ru/login.php?referer=https%3A%2F%2Fwww.lostfilm.tv%2F',
                            text=self.read_httpretty_content(u'test_lostfilmtracker.1.login1.bogi.ru.html',
                                                             encoding='utf-8'))

        # hack for pass multiple cookies
        mocker.register_uri(requests_mock.POST,
                            u'http://www.lostfilm.tv/blg.php?ref=random',
                            text=u'Internal server error', status_code=500)

        with self.assertRaises(LostFilmTVLoginFailedException) as cm:
            self.tracker.login(u'fakelogin', u'p@$$w0rd')
        self.assertEqual(cm.exception.code, -2)
        self.assertIsNone(cm.exception.text)
        self.assertIsNone(cm.exception.message)

    @requests_mock.Mocker()
    def test_httpretty_unknown_login_failed_2(self, mocker):
        """
        :type mocker: requests_mock.Mocker
        """
        mocker.register_uri(requests_mock.POST,
                            'https://login1.bogi.ru/login.php?referer=https%3A%2F%2Fwww.lostfilm.tv%2F',
                            text='', status_code=302,
                            headers={'location': 'http://some-error.url/error.php'})
        mocker.register_uri(requests_mock.GET,
                            'http://some-error.url/error.php',
                            text='', status_code=200)

        with self.assertRaises(LostFilmTVLoginFailedException) as cm:
            self.tracker.login('fakelogin', 'p@$$w0rd')
        self.assertEqual(cm.exception.code, -1)
        self.assertIsNone(cm.exception.text)
        self.assertIsNone(cm.exception.message)
