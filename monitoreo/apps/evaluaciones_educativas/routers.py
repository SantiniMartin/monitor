# routers.py

class SecondaryDBRouter:
    # Nombre real del app_label
    route_apps = {'evaluaciones_educativas'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_apps:
            return 'Evaluacion'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_apps:
            return 'Evaluacion'
        return 'default'

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_apps:
            return db == 'Evaluacion'
        return db == 'default'
