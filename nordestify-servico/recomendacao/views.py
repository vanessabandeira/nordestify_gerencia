from django.shortcuts import render
from django.http import HttpResponse
from recomendacao.models import Users, Reviews
from recomendacao.Algoritmos import GetNeighbors, Preprocessamento, RecomendaMusicas
from django.core import serializers
from django.http import JsonResponse

def userNeighbors(request, userid):

    usuario = Users.objects.get(pk=userid)
    usuarios = Users.objects.all()
    resultado = GetNeighbors(usuario, usuarios, 5)

    return JsonResponse(resultado, safe=False)


def musicsRecommendation (request, userid):
    usuario = Users.objects.get(pk=userid)
    usuarios = Users.objects.all()
    usuariosNeighbors = GetNeighbors(usuario, usuarios, 5)

    preprocessamento = Preprocessamento(usuario, usuariosNeighbors)
    recomendacoes = RecomendaMusicas(usuario, preprocessamento)

    return JsonResponse(recomendacoes, safe=False)

