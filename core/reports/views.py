﻿import sys
import os
import core
import os.path
import subprocess

from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect
from django.template.loader import get_template
from django.template import Context
from django.shortcuts  import render_to_response, get_object_or_404, redirect
from django.core.urlresolvers import reverse

from core.models import Tag, ArticleDetails
from core.models import Feedback, Rating, Topic
from core.models import Info, ArticleRating, User
from core.views import login

import time
import memcache
from datetime import datetime
from operator import attrgetter
from sharek import settings

# get first memcached URI
mc = memcache.Client([settings.MEMCACHED_BACKEND])

def infographic(request, type=''):
    user = None

    login(request)

    if request.user.is_authenticated():
      user = request.user

    template_context = {'type': type, 'settings': settings, 'user':user,}

    return render_to_response('charts/infographic.html', template_context ,RequestContext(request))

def comments_chart(request):
    user = None

    login(request)

    if request.user.is_authenticated() and request.user.is_staff:
      user = request.user
    else:
        return HttpResponseRedirect(reverse('index'))

    chart_data = mc.get('chart_data')
    if not chart_data:
         chart_data = Feedback.objects.feedback_charts()
         mc.set('chart_data', chart_data, settings.MEMCACHED_TIMEOUT)

    context = Context({'user': user, 'chart_data': chart_data})

    return render_to_response('charts/comments.html', context ,RequestContext(request))

def comments_pdf(request, article_slug=None):
    user = None

    login(request)

    if request.user.is_authenticated() and request.user.is_staff:
      user = request.user
    else:
        return HttpResponseRedirect(reverse('index'))

    if article_slug:
        article = get_object_or_404( ArticleDetails, slug=article_slug )

    inactive_users = User.get_inactive

    comments = Feedback.objects.filter(articledetails_id = article.id, parent_id = None).order_by('-id').exclude(user__in=inactive_users)

    dt_obj = datetime.now()
    date_display = dt_obj.strftime("%Y-%m-%d")

    context = Context({'article':article, 'comments':comments, 'date_display': date_display})

    kwargs = {}

    if request.GET and request.GET.get('as', '') == 'html':
        return render_to_response('reports/comments_template.html', context ,RequestContext(request))

    else:
        return render_to_pdf('reports/comments_template.html', 'comments_template_', context, 'article_' + article.slug)

def topics_pdf(request):

    return HttpResponseRedirect("http://bit.ly/dostor-masr")

    user = None

    login(request)

    if request.user.is_authenticated():
      user = request.user

    topics = Topic.objects.all().order_by('order')

    dt_obj = datetime.now()
    date_str = dt_obj.strftime("%Y%m%d_%H%M%S")
    date_display = dt_obj.strftime("%Y-%m-%d")

    context = Context({'topics':topics, 'date_display': date_display})

    kwargs = {}

    if request.GET and request.GET.get('as', '') == 'html':
        return render_to_response('reports/topics_template.html', context ,RequestContext(request))

    else:
        return render_to_pdf('reports/topics_template.html', 'topics_template_', context, 'dostor_masr')

def topic_pdf(request, topic_slug=None):
    user = None

    login(request)

    if request.user.is_authenticated():
      user = request.user

    if topic_slug:
        topic = mc.get('topic_' + str(topic_slug))
        if not topic:
             topic = get_object_or_404( Topic, slug=topic_slug )
             mc.set('topic_' + str(topic_slug), topic, settings.MEMCACHED_TIMEOUT)
    
        articles = mc.get(str(topic_slug) + '_articles')
        if not articles:
             articles = topic.get_articles()
             mc.set(str(topic_slug) + '_articles', articles, settings.MEMCACHED_TIMEOUT)

    dt_obj = datetime.now()
    date_str = dt_obj.strftime("%Y%m%d_%H%M%S")
    date_display = dt_obj.strftime("%Y-%m-%d")

    context = Context({'topic':topic, 'articles':articles, 'date_display': date_display})

    kwargs = {}

    if request.GET and request.GET.get('as', '') == 'html':
        return render_to_response('reports/topic_template.html', context ,RequestContext(request))

    else:
        return render_to_pdf('reports/topic_template.html', 'topic_template_', context, 'topic_' + topic.slug)

def export_feedback(request, article_slug):
    
    user = None
    login(request)

    
    if request.user.is_authenticated() and request.user.is_staff:
      user = request.user
    else:
      return HttpResponseRedirect(reverse('index'))
    
    #Retrieve data or whatever you need
    articles = ArticleDetails.objects.all()
    articles =  sorted(articles,  key=attrgetter('header.topic.id','header.order','id'))
    article = get_object_or_404( ArticleDetails, slug=article_slug )
    feedback = Feedback.objects.filter(articledetails_id = article.id)

    template_context = {'article':article, 'articles':articles, 'feedbacks':feedback}
    return render_to_response('reports/export_feedback.html', template_context ,RequestContext(request))

def render_to_pdf(template_html, template_prefix, context, pdf_filename):

     dt_obj = datetime.now()
     date_str = dt_obj.strftime("%Y%m%d_%H%M%S")
     date_display = dt_obj.strftime("%Y-%m-%d")

     template = loader.get_template(template_html)
     rendered = template.render(context)
     full_temp_html_file_name = core.__path__[0] + '/static/temp/' + template_prefix + date_str + '.html'
     file= open(full_temp_html_file_name, 'w')
     file.write(rendered.encode('utf8'))
     file.close( )

     command_args = 'wkhtmltopdf -L 10 -R 10 -T 20 -B 10 --footer-html ' + core.__path__[0] + '/static/footer.html ' + full_temp_html_file_name + ' -'
     popen = subprocess.Popen(command_args, bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
     pdf_contents = popen.stdout.read()
     popen.terminate()
     popen.wait()

     response = HttpResponse(pdf_contents, mimetype='application/pdf')
     response['Content-Disposition'] = 'filename=' + pdf_filename + '.pdf'
     return response

