# -*- coding: utf-8 -*-

from __future__ import print_function
import Backend
import datetime, pytz
import HumanTime
import OsmDiff as osmdiff
import OsmChangeset as oc
import operator
import os
import logging
import jinja2

logger = logging.getLogger(__name__)

class Backend(Backend.Backend):

    def __init__(self, config, subcfg):
        super(Backend, self).__init__(config, subcfg)
        self.list_fname = config.getpath('path', 'BackendHtml')+'/'+subcfg['filename']
        self.template_name = subcfg['template']

        self.show_details = getattr(subcfg, 'show_details', True)
        self.show_comments = getattr(subcfg, 'show_comments', True)
        self.last_chg_seen = None
        self.last_update = datetime.datetime.now()

        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(config.getpath('template_path', 'tracker')))
        self.env.filters['js_datetime'] = self._js_datetime_filter
        self.env.filters['utc_datetime'] = self._utc_datetime_filter

        self.start_page(self.list_fname)
        self.no_items()
        self.end_page()

    def _js_datetime_filter(self, value):
        '''Jinja2 filter formatting timestamps in format understood by javascript'''
            # See javascript date/time format: http://tools.ietf.org/html/rfc2822#page-14
        JS_TIMESTAMP_FMT = '%a, %d %b %Y %H:%M:%S %z'
        return value.strftime(JS_TIMESTAMP_FMT)

    def _utc_datetime_filter(self, value):
        TIMESTAMP_FMT = '%Y:%m:%d %H:%M:%S'
        return value.strftime(TIMESTAMP_FMT)

    def print_state(self, db):
        now = datetime.datetime.now()
        #if now.day != self.last_update.day:
        #    print('Cycler - new day: {} {}'.format(now.day, self.last_update.day))
        #period = now-state.cset_start_time
        #if period.total_seconds() > self.config.get('horizon_hours', 'tracker')*3600:
        #    os.rename(self.list_fname, self.list_fname_old)
        #    print('Cycler')
        #    state.clear_csets()
        self.last_update = datetime.datetime.now()
        if self.generation != db.generation:
            self.generation = db.generation

            self.start_page(self.list_fname)
            template = self.env.get_template(self.template_name)
            ctx = { 'csets': [],
                    'csets_err': [],
                    'csetmeta': {},
                    'csetinfo': {},
                    'show_details': self.show_details,
                    'show_comments': self.show_comments }
            notes = 0
            csets_w_notes = 0
            csets_w_addr_changes = 0
            for c in db.chgsets_ready(state=[db.STATE_CLOSED, db.STATE_OPEN, db.STATE_ANALYZING2, db.STATE_DONE]):
                cid = c['cid']
                ctx['csets'].append(c)
                info = db.chgset_get_info(cid)
                meta = db.chgset_get_meta(cid)
                ctx['csetmeta'][cid] = meta
                if info:
                    ctx['csetinfo'][cid] = info
                else:
                    logger.warn('No info for cid {}: {}'.format(cid, c))
                if meta['open'] or (info and 'truncated' in info['state']):
                    continue
                notecnt = int(meta['comments_count'])  # FIXME: This is duplicate w. BackendHtmlSummary.py
                if notecnt > 0:
                    notes += int(meta['comments_count'])
                    csets_w_notes += 1
                if c['state'] != db.STATE_DONE:
                    continue
                if not 'dk_address_node_changes' in info['misc']:
                    logger.error('No dk_address_node_changes key found')
                    logger.error('cset: {}'.format(c))
                    logger.error('meta: {}'.format(meta))
                    logger.error('info: {}'.format(info))

                if int(info['misc']['dk_address_node_changes'])>0:
                    csets_w_addr_changes += 1
            ctx['csets_with_notes'] = csets_w_notes
            ctx['csets_with_addr_changes'] = csets_w_addr_changes
            logger.debug('Data passed to template: {}'.format(ctx))
            self.pprint(template.render(ctx))
            self.end_page()

    def pprint(self, txt):
        print(txt.encode('utf8'), file=self.f)
        #print('*'+txt)

    def start_page(self, fname):
        self.f = open(fname, 'w', os.O_TRUNC)
        self.pprint('<!-- Generated by OpenStreetMap Analytic Difference Engine -->')

    def end_page(self):
        self.f.close()
        self.f = None

    def no_items(self, state=None):
        if state:
            time = state.timestamp.strftime('%Y:%m:%d %H:%M:%S')
        else:
            time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
            time = time.strftime('%Y:%m:%d %H:%M:%S')
        self.pprint('<p>No changesets at '+time+' (UTC)</p>')
