# This file is part of the JACoW plugin.
# Copyright (C) 2021 - 2024 CERN
#
# The CERN Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License; see
# the LICENSE file for more details.

from flask import g, session
from flask_pluginengine import render_plugin_template
from wtforms.fields import BooleanField

from indico.core import signals
from indico.core.db import db
from indico.core.plugins import IndicoPlugin, url_for_plugin
from indico.modules.events.abstracts.forms import AbstractForm
from indico.modules.events.abstracts.views import WPDisplayAbstracts, WPManageAbstracts
from indico.modules.events.contributions.forms import ContributionForm
from indico.modules.events.contributions.views import WPContributions, WPManageContributions, WPMyContributions
from indico.modules.events.layout.util import MenuEntryData
from indico.modules.events.persons.schemas import PersonLinkSchema
from indico.util.i18n import _
from indico.web.forms.base import IndicoForm
from indico.web.forms.widgets import SwitchWidget
from indico.web.menu import SideMenuItem

from indico_jacow.blueprint import blueprint
from indico_jacow.models.affiliations import AbstractAffiliations, ContributionAffiliations


class SettingsForm(IndicoForm):
    sync_enabled = BooleanField(_('Sync profiles'), widget=SwitchWidget(),
                                description=_('Periodically sync user details with the central database'))


class JACOWPlugin(IndicoPlugin):
    """JACoW

    Provides utilities for JACoW Indico
    """

    configurable = True
    settings_form = SettingsForm
    default_settings = {
        'sync_enabled': False,
    }

    def init(self):
        super().init()
        self.template_hook('abstract-list-options', self._inject_abstract_export_button)
        self.template_hook('contribution-list-options', self._inject_contribution_export_button)
        self.template_hook('custom-affiliation', self._inject_custom_affiliation)
        self.connect(signals.core.form_validated, self._form_validated)
        self.connect(signals.event.sidemenu, self._extend_event_menu)
        self.connect(signals.menu.items, self._add_sidemenu_item, sender='event-management-sidemenu')
        self.connect(signals.plugin.schema_pre_load, self._person_link_schema_pre_load, sender=PersonLinkSchema)
        self.connect(signals.plugin.schema_post_dump, self._person_link_schema_post_dump, sender=PersonLinkSchema)
        self.inject_bundle('main.js', WPContributions)
        self.inject_bundle('main.js', WPDisplayAbstracts)
        self.inject_bundle('main.js', WPManageAbstracts)
        self.inject_bundle('main.js', WPManageContributions)
        self.inject_bundle('main.js', WPMyContributions)

    def _inject_abstract_export_button(self, event=None):
        return render_plugin_template('export_button.html',
                                      csv_url=url_for_plugin('jacow.abstracts_csv_export_custom', event),
                                      xlsx_url=url_for_plugin('jacow.abstracts_xlsx_export_custom', event))

    def _inject_contribution_export_button(self, event=None):
        return render_plugin_template('export_button.html',
                                      csv_url=url_for_plugin('jacow.contributions_csv_export_custom', event),
                                      xlsx_url=url_for_plugin('jacow.contributions_xlsx_export_custom', event))

    def _inject_custom_affiliation(self, person=None):
        return render_plugin_template('custom_affiliation.html', person=person)

    def _form_validated(self, form, **kwargs):
        context = None
        if isinstance(form, ContributionForm):
            context = 'contribution'
        elif isinstance(form, AbstractForm):
            context = 'abstract'
        if not context:
            return
        jacow_affiliations_data = g.pop('jacow_affiliations_data', None)
        if not jacow_affiliations_data:
            return
        person_links = form.person_link_data.data if context == 'contribution' else form.person_links.data
        affiliations_cls = ContributionAffiliations if context == 'contribution' else AbstractAffiliations
        for person_link in person_links:
            person_data = jacow_affiliations_data.get(person_link.person.identifier)
            if person_data is None:
                continue
            person_link.jacow_affiliations = [affiliations_cls(affiliation_id=id)
                                              for id in person_data['jacow_affiliations_ids']]
        db.session.flush()

    def _extend_event_menu(self, sender, **kwargs):
        def _statistics_visible(event):
            if not session.user or not event.has_feature('abstracts'):
                return False
            return any(track.can_review_abstracts(session.user) for track in event.tracks)

        return MenuEntryData(title=_('My Statistics'), name='abstract_reviewing_stats',
                             endpoint='jacow.reviewer_stats', position=1, parent='call_for_abstracts',
                             visible=_statistics_visible)

    def _add_sidemenu_item(self, sender, event, **kwargs):
        if not event.can_manage(session.user) or not event.has_feature('abstracts'):
            return
        return SideMenuItem('abstracts_stats', _('CfA Statistics'),
                            url_for_plugin('jacow.abstracts_stats', event), section='reports')

    def _person_link_schema_pre_load(self, sender, data, **kwargs):
        jacow_data = {k: data.pop(k) for k in list(data) if k.startswith('jacow_')}
        identifier = data.get('identifier')
        if identifier is None:
            if 'person_id' not in data:
                # XXX: we do not support manually entered persons for now
                return
            identifier = f"EventPerson:{data['person_id']}"
        if hasattr(g, 'jacow_affiliations_data'):
            g.jacow_affiliations_data[identifier] = jacow_data
        else:
            g.jacow_affiliations_data = {identifier: jacow_data}

    def _person_link_schema_post_dump(self, sender, data, orig, **kwargs):
        for person, person_link in zip(data, orig):
            person['jacow_affiliations_ids'] = [ja.affiliation.id for ja in person_link.jacow_affiliations]
            person['jacow_affiliations_meta'] = [ja.details for ja in person_link.jacow_affiliations]

    def get_blueprints(self):
        return blueprint
