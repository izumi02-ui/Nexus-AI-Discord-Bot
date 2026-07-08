"""
Project Nexus

Service Registry
"""


class Registry:

    def __init__(self):

        self.services = {}

    def register(self, name, service):

        self.services[name] = service

    def get(self, name):

        return self.services.get(name)


registry = Registry()
