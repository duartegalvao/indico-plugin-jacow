// This file is part of the JACoW plugin.
// Copyright (C) 2021 - 2024 CERN
//
// The CERN Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License; see
// the LICENSE file for more details.

import {registerPluginComponent, registerPluginObject} from 'indico/utils/plugins';

import MultipleAffiliationsSelector, {
  MultipleAffiliationsButton,
  customFields,
  onAddPersonLink,
} from './MultipleAffiliationsSelector';

const PLUGIN_NAME = 'jacow';

registerPluginComponent(PLUGIN_NAME, 'personListItemActions', MultipleAffiliationsButton);
registerPluginComponent(PLUGIN_NAME, 'personLinkFieldModals', MultipleAffiliationsSelector);
registerPluginObject(PLUGIN_NAME, 'personLinkCustomFields', customFields);
registerPluginObject(PLUGIN_NAME, 'onAddPersonLink', onAddPersonLink);
