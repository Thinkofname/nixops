# -*- coding: utf-8 -*-

import time
import nixops.util
import nixops.resources
import CloudFlare


class CloudflareZoneDefinition(nixops.resources.ResourceDefinition):
    """Definition of a Cloudflare zone."""

    @classmethod
    def get_type(cls):
        return "cloudflare-zone"

    @classmethod
    def get_resource_type(cls):
        return "cloudflareZones"

    def __init__(self, xml, config):
        super(CloudflareZoneDefinition, self).__init__(xml)
        self.zone = xml.find("attrs/attr[@name='zone']/string").get("value")
        self.email = xml.find("attrs/attr[@name='email']/string").get("value")
        self.token = xml.find("attrs/attr[@name='token']/string").get("value")
        self.records = config['records'];


    def show_type(self):
        return "{0}".format(self.get_type())


class CloudflareZoneState(nixops.resources.ResourceState):
    """State of a Cloudflare zone."""

    state = nixops.util.attr_property("state", nixops.resources.ResourceState.MISSING, int)
    email = nixops.util.attr_property("cloudflare.email", None)
    token = nixops.util.attr_property("cloudflare.token", None)
    zone = nixops.util.attr_property("cloudflare.zone", None)
    records = nixops.util.attr_property("cloudflare.records", {}, 'json')


    @classmethod
    def get_type(cls):
        return "cloudflare-zone"

    def __init__(self, depl, name, id):
        nixops.resources.ResourceState.__init__(self, depl, name, id)
        self._client = None

    def show_type(self):
        s = super(CloudflareZoneState, self).show_type()
        if self.state == self.UP: s = "{0} [{1}]".format(s, self.region)
        return s

    @property
    def resource_id(self):
        return self.zone

    def create(self, defn, check, allow_reboot, allow_recreate):
        self.zone = defn.zone
        self.email = defn.email
        self.token = defn.token
        if self._client == None:
            self._client = CloudFlare.CloudFlare(email = self.email, token = self.token)

        zones = self._client.zones.get(params = {'name': self.zone})
        zone_id = zones[0]['id']

        active_records = {}
        old_records = self.records

        for t, tys in defn.records.iteritems():
            ty = t.upper()
            active_ty =  {};
            active_records[ty] = active_ty
            old_ty = old_records[ty] if ty in old_records else {};
            for name, names in tys.iteritems():
                active_name =  [];
                active_ty[name] = active_name
                old_name = old_ty[name] if name in old_ty else [];
                for r in names:
                    if r['content'].startswith("res-"):
                        machine = self.depl.get_machine(r['content'][4:])
                        if ty == "AAAA":
                            r['content'] = machine.public_ipv6
                        else:
                            r['content'] = machine.public_ipv4
                    old = filter(lambda x: x['content'] == r['content'], old_name)
                    if len(old) != 0:
                        o = old[0]
                        old_name.remove(o)
                        if o['proxied'] != r['proxied']:
                            self.log("updating dns record '{} {}'".format(ty, name))
                            self._client.zones.dns_records.put(zone_id, o['id'], data = {
                                'name': name,
                                'type': ty,
                                'content': r['content'],
                                'proxied': r['proxied'],
                            })
                            o['proxied'] = r['proxied']
                        active_name.append(o)
                    else:
                        self.log("creating dns record '{} {}'".format(ty, name))
                        param = dict(r)
                        param['name'] = name;
                        param['type'] = ty;
                        result = self._client.zones.dns_records.post(zone_id, data = param)
                        active_name.append(result)

        for t, tys in old_records.iteritems():
            ty = t.upper()
            for name, names in tys.iteritems():
                for r in names:
                    self.log("removing dns record '{} {}'".format(ty, name))
                    self._client.zones.dns_records.delete(zone_id, r['id'])

        self.records = active_records

    def destroy(self, wipe=False):
        if self._client == None:
            self._client = CloudFlare.CloudFlare(email = self.email, token = self.token)
        zones = self._client.zones.get(params = {'name': self.zone})
        zone_id = zones[0]['id']
        for t, tys in self.records.iteritems():
            ty = t.upper()
            for name, names in tys.iteritems():
                for r in names:
                    self.log("removing dns record '{} {}'".format(ty, name))
                    self._client.zones.dns_records.delete(zone_id, r['id'])
        self.records = {}
        return True
