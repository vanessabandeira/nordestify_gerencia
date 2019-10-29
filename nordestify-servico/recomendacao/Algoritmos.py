import operator
import math
from recomendacao.models import Reviews, Musics, Users
from django.db.models import Max, Min
from collections import Counter


# KNN entre os usuários

# Função para calcular as distancias
# a = usuário logado, b = usuário a ser comparado
def ComputeDistance(a, b):
    total = 0
    reviewsUserA = Reviews.objects.filter(user=a.id)
    reviewsUserB = Reviews.objects.filter(user=b.id)
    quantidadeItens = len(reviewsUserA)

    for reviewA in reviewsUserA:
        for reviewB in reviewsUserB:
            if reviewA.music_id == reviewB.music_id:
                # Atribui uma pontuação
                if reviewA.review == reviewB.review:
                    total = total + 1
                elif reviewA.review != reviewB.review:
                    if total > 0:
                        total = total - 1
    distancia = total / quantidadeItens
    return distancia


# Função para pegar os K usuários mais próximos
def GetNeighbors(user, users, K):
    distances = []
    for index, userTemp in enumerate(users):
        if user.id != userTemp.id:
            dist = ComputeDistance(user, userTemp)
            distances.append((userTemp.id, dist, userTemp.name, userTemp.avatar))
    distances.sort(key=operator.itemgetter(1), reverse=True)
    neighbors = []
    for x in range(K):
        try:
            neighbors.append({'id': distances[x][0], 'score': distances[x][1], 'name': distances[x][2],
                              'avatar': distances[x][3]})
        except:
            # Debug
            print("Sem mais usuários disponíveis")
    return neighbors


# Recomendação de músicas

# Faz o pre-processamento
# user é o usuário logado e usersNeighbors são os usuários calculados no GetNeighbors
# Retorna um array de musicas = [id, positiva, negativa, preliminar1, preliminar2, ocorrencias, score]
def Preprocessamento(user, usersNeighbors):
    userReviews = Reviews.objects.filter(user=user.id)

    # Transforma o QuerySet do usuário em um array
    userReviewsArray = []
    for review in userReviews:
        userReviewsArray.append(review)

    # Transforma o QuerySet dos usuários em um array
    usersReviewsArray = []
    for users in usersNeighbors:
        reviews = Reviews.objects.filter(user=users['id'])
        for review in reviews:
            usersReviewsArray.append(review)

    # Limpa o usersReviewsArray, retirando os itens que o usuário ja avaliou anteriormente
    musicas = []
    for usersReview in usersReviewsArray:
        repetiu = False
        for userReview in userReviewsArray:
            if usersReview.music_id == userReview.music_id:
                repetiu = True
                break
        if not repetiu:
            musicas.append(
                {'id': usersReview.music_id, 'positiva': 0, 'negativa': 0, 'preliminar1': 0.0, 'preliminar2': 0.0,
                 'ocorrencias': 1, 'score': 0.0})

    # Retira os itens repetidos e atualiza a coluna de ocorrencias
    musicasTemp = []
    for musica in musicas:
        achou = False
        for musica2 in musicasTemp:
            if musica['id'] == musica2['id']:
                achou = True
                musica2['ocorrencias'] = musica2['ocorrencias'] + 1
        if not achou:
            musicasTemp.append(musica)
    musicas = musicasTemp

    # Conta as avalicações positivas e negativas
    for musica in musicas:
        for review in usersReviewsArray:
            if musica['id'] == review.music_id:
                if review.review == 1:
                    musica['positiva'] = musica['positiva'] + 1
                elif review.review == -1:
                    musica['negativa'] = musica['negativa'] + 1

    # Retira os itens onde negativo > positivo e calcula o primeiro score preliminar
    musicasTemp = []
    for musica in musicas:
        if musica['positiva'] >= musica['negativa']:
            musica['preliminar1'] = (musica['positiva'] - musica['negativa']) / musica['ocorrencias']
            musicasTemp.append(musica)
    musicas = musicasTemp

    return musicas


# Recebe um usuário e retorna a id do gênero mais bem avaliado pelo usuário
def GeneroModa(user):
    reviews = Reviews.objects.filter(user=user.id, review=1)

    generos = []
    for review in reviews:
        musica = Musics.objects.get(id=review.music_id)
        generos.append(musica.genre.id)

    data = Counter(generos)
    return data.most_common()[0][0]


# Função auxilixar para normalizar os valores
def Normalizar(x, max, min):
    resultado = (x - min) / (max - min)
    return resultado


# Função para calcular a distância entre as músicas
def ComputeDistanceMusics(a, b):
    # Essa pontuação corresponde a 1/3 do score final
    calcula = math.sqrt(math.pow(a['danceability'] - b.danceability, 2) + math.pow(a['energy'] - b.energy, 2) +
                        math.pow(a['loudness'] - b.loudness, 2) + math.pow(a['speechiness'] - b.speechiness, 2) +
                        math.pow(a['acousticness'] - b.acousticness, 2) + math.pow(
        a['instrumentalness'] - b.instrumentalness, 2) +
                        math.pow(a['liveness'] - b.liveness, 2) + math.pow(a['valence'] - b.valence, 2))

    # Se as músicas tiverem os gêneros iguais, deve atribuir uma pontuação equivalente a 2/3 do score final
    temp = 0
    if a['genero'] == b.genre.id:
        temp = 1

    # DEBUG
    print("Pontuacao: " + str(((calcula/2) + (temp/2))/2))
    return ((calcula/2) + (temp/2))/2


# Recebe uma música e uma lista de músicas e retorna a distância entre elas
def GetNeighborsMusic(musica, musicas):
    distances = []
    for index, musicaTemp in enumerate(musicas):
        dist = ComputeDistanceMusics(musica, musicaTemp)
        distances.append({'id': musicaTemp.id, 'score': dist, 'capa': musicaTemp.artist.photo, 'name': musicaTemp.name, 'artist': musicaTemp.artist.name})
        # DEBUG
        print("ID: " + str(musicaTemp.id) + " Score: " + str(dist))
    return distances


# Recebe um usuário e uma lista de músicas vindo do Pre-processamento
def RecomendaMusicas(user, musicas):
    musicas.sort(key=operator.itemgetter('preliminar1'), reverse=True)

    # Seleciona as músicas no banco de dados
    musicasList = []
    for musica in musicas:
        musicasList.append(Musics.objects.get(id=musica['id']))

    # Normaliza os valores de loudness
    max = Musics.objects.all().aggregate(Max('loudness'))['loudness__max']
    min = Musics.objects.all().aggregate(Min('loudness'))['loudness__min']
    for musica in musicasList:
        musica.loudness = Normalizar(musica.loudness, max, min)

    # Cria uma música fictícia, que armazena a média das características das músicas
    # musicaFicticia = [danceability, energy, loudness, speechiness, acousticness, instrumentalness, liveness, valence, tempo]
    musicaFicticia = {'danceability': 0.0, 'energy': 0.0, 'loudness': 0.0, 'speechiness': 0.0, 'acousticness': 0.0,
                      'instrumentalness': 0.0, 'liveness': 0.0, 'valence': 0.0, 'tempo': 0.0, 'genero': 0}

    reviews = Reviews.objects.filter(user=user.id, review=1)
    musicasReview = []
    for review in reviews:
        musicasReview.append(Musics.objects.get(id=review.music_id))

    count = 1
    for musica in musicasReview:
        if count <= 5:
            musicaFicticia['danceability'] += musica.danceability
            musicaFicticia['energy'] += musica.energy
            musicaFicticia['loudness'] += musica.loudness
            musicaFicticia['speechiness'] += musica.speechiness
            musicaFicticia['acousticness'] += musica.acousticness
            musicaFicticia['instrumentalness'] += musica.instrumentalness
            musicaFicticia['liveness'] += musica.liveness
            musicaFicticia['valence'] += musica.valence
            musicaFicticia['tempo'] += musica.tempo
            count += 1
        else:
            break

    # Calcula a média
    musicaFicticia['danceability'] = musicaFicticia['danceability'] / 5
    musicaFicticia['energy'] = musicaFicticia['energy'] / 5
    musicaFicticia['loudness'] = Normalizar(musicaFicticia['loudness'] / 5, max, min)
    musicaFicticia['speechiness'] = musicaFicticia['speechiness'] / 5
    musicaFicticia['acousticness'] = musicaFicticia['acousticness'] / 5
    musicaFicticia['instrumentalness'] = musicaFicticia['instrumentalness'] / 5
    musicaFicticia['liveness'] = musicaFicticia['liveness'] / 5
    musicaFicticia['valence'] = musicaFicticia['valence'] / 5
    musicaFicticia['tempo'] = musicaFicticia['tempo'] / 5
    musicaFicticia['genero'] = GeneroModa(user)

    # DEBUG
    print("Genero: " + str(musicaFicticia['genero']) + " User: " + user.name)
    print("Musica: " + str(musicaFicticia))

    # Calcula as distâncias entre a música ficticia e a lista de música
    neighbors = GetNeighborsMusic(musicaFicticia, musicasList)
    for index, neighbor in enumerate(neighbors):
        musicas[index]['preliminar2'] = neighbor['score']
        musicas[index]['name'] = neighbor['name']
        musicas[index]['capa'] = neighbor['capa']
        musicas[index]['artist'] = neighbor['artist']

    # Normaliza Score Preliminar2 e calcula Score Final
    for index, musica in enumerate(musicas):
        musicas[index]['score'] = (musicas[index]['preliminar1'] / 2) + (musicas[index]['preliminar2'] / 2)
        print("ID: " + str(musicas[index]['id']) + "Score1: " + str(musicas[index]['preliminar1'] / 2) + " Score2: " + str(musicas[index]['preliminar2'] / 2))

    # Gera o resultado final
    musicas.sort(key=operator.itemgetter('score'), reverse=True)
    resultado = []

    for x in range(5):
        resultado.append(musicas[x])

    return resultado
