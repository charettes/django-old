from django.forms import models as model_forms
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import (SingleObjectMixin,
                        SingleObjectTemplateResponseMixin, BaseDetailView)


class FormMixin(object):
    """
    A mixin that provides a way to show and handle a form in a request.
    """

    initial = {}
    form_class = None
    success_url = None

    def get_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        return self.initial

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        return self.form_class

    def get_form(self, form_class):
        """
        Returns an instance of the form to be used in this view.
        """
        return form_class(**self.get_form_kwargs())

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = {'initial': self.get_initial()}
        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
                'files': self.request.FILES,
            })
        return kwargs

    def get_context_data(self, **kwargs):
        return kwargs

    def get_success_url(self):
        if self.success_url:
            url = self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def form_valid(self, form):
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class ModelFormMixin(FormMixin, SingleObjectMixin):
    """
    A mixin that provides a way to show and handle a modelform in a request.
    """

    def get_form_class(self):
        """
        Returns the form class to use in this view
        """
        if self.form_class:
            return self.form_class
        else:
            if self.model is not None:
                # If a model has been explicitly provided, use it
                model = self.model
            elif hasattr(self, 'object') and self.object is not None:
                # If this view is operating on a single object, use
                # the class of that object
                model = self.object.__class__
            else:
                # Try to get a queryset and extract the model class
                # from that
                model = self.get_queryset().model
            return model_forms.modelform_factory(model)

    def get_form_kwargs(self):
        """
        Returns the keyword arguments for instanciating the form.
        """
        kwargs = super(ModelFormMixin, self).get_form_kwargs()
        kwargs.update({'instance': self.object})
        return kwargs

    def get_success_url(self):
        if self.success_url:
            url = self.success_url % self.object.__dict__
        else:
            try:
                url = self.object.get_absolute_url()
            except AttributeError:
                raise ImproperlyConfigured(
                    "No URL to redirect to.  Either provide a url or define"
                    " a get_absolute_url method on the Model.")
        return url

    def form_valid(self, form):
        self.object = form.save()
        return super(ModelFormMixin, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = kwargs
        if self.object:
            context['object'] = self.object
            context_object_name = self.get_context_object_name(self.object)
            if context_object_name:
                context[context_object_name] = self.object
        return context


class ProcessFormView(View):
    """
    A mixin that processes a form on POST.
    """
    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        return self.render_to_response(self.get_context_data(form=form))

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    # PUT is a valid HTTP verb for creating (with a known URL) or editing an
    # object, note that browsers only support POST for now.
    def put(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class BaseFormView(FormMixin, ProcessFormView):
    """
    A base view for displaying a form
    """


class FormView(TemplateResponseMixin, BaseFormView):
    """
    A view for displaying a form, and rendering a template response.
    """


class SuccessMessageMixin(object):
    """
    A mixin providing the ability to create success messages.
    Message creation can be disabled by setting success_message=None.
    """
    def get_success_message(self, **kwargs):
        return self.success_message % kwargs
    
    def create_success_message(self, request, **kwargs):
        try:
            msg = self.get_success_message(**kwargs)
        except AttributeError:
            raise ImproperlyConfigured('`SuccessMessageMixin` subclasses must define a '
                                       '`success_message` or override `get_success_message`')
        except TypeError:
            if self.success_message is not None:
                raise
        else:
            messages.success(request, msg, fail_silently=True)


class BaseCreateView(ModelFormMixin, ProcessFormView, SuccessMessageMixin):
    """
    Base view for creating an new object instance.

    Using this base class requires subclassing to provide a response mixin.
    """
    success_message = _("The %(verbose_name)s was created successfully.")
    
    def get(self, request, *args, **kwargs):
        self.object = None
        return super(BaseCreateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        return super(BaseCreateView, self).post(request, *args, **kwargs)
    
    def form_valid(self, form):
        form_valid = super(BaseCreateView, self).form_valid(form)
        self.create_success_message(self.request, object=self.object,
                                    verbose_name=self.object._meta.verbose_name)
        return form_valid


class CreateView(SingleObjectTemplateResponseMixin, BaseCreateView):
    """
    View for creating an new object instance,
    with a response rendered by template.
    """
    template_name_suffix = '_form'


class BaseUpdateView(ModelFormMixin, ProcessFormView, SuccessMessageMixin):
    """
    Base view for updating an existing object.

    Using this base class requires subclassing to provide a response mixin.
    """
    success_message = _("The %(verbose_name)s was updated successfully.")
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(BaseUpdateView, self).post(request, *args, **kwargs)
    
    def form_valid(self, form):
        form_valid = super(BaseUpdateView, self).form_valid(form)
        self.create_success_message(self.request, object=self.object,
                                    verbose_name=self.object._meta.verbose_name)
        return form_valid


class UpdateView(SingleObjectTemplateResponseMixin, BaseUpdateView):
    """
    View for updating an object,
    with a response rendered by template..
    """
    template_name_suffix = '_form'


class DeletionMixin(object):
    """
    A mixin providing the ability to delete objects
    """
    success_url = None

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        return HttpResponseRedirect(self.get_success_url())

    # Add support for browsers which only accept GET and POST for now.
    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)

    def get_success_url(self):
        if self.success_url:
            return self.success_url
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")


class BaseDeleteView(DeletionMixin, BaseDetailView, SuccessMessageMixin):
    """
    Base view for deleting an object.

    Using this base class requires subclassing to provide a response mixin.
    """
    success_message = _("The %(verbose_name)s was deleted.")
    
    def delete(self, request, *args, **kwargs):
        response = super(BaseDeleteView, self).delete(request, *args, **kwargs)
        self.create_success_message(request, object=self.object,
                                    verbose_name=self.object._meta.verbose_name)
        return response


class DeleteView(SingleObjectTemplateResponseMixin, BaseDeleteView):
    """
    View for deleting an object retrieved with `self.get_object()`,
    with a response rendered by template.
    """
    template_name_suffix = '_confirm_delete'
