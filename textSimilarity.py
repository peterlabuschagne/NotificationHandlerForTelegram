from collections import Counter
import numpy as np
import time
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity as cosineSimilarity

class TextSimilarity:
    def GetCosineSimilarity(self,vectors): 
        vectors = [t for t in vectors]
        return cosineSimilarity(vectors,)

    def CustomCosineSimilarity(self,a,b):
        result = np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))
        return result

    def GetVectorsAndFeatures(self,strs):
        text = [t for t in strs]
        vectorizer = CountVectorizer(text)
        vectorizer.fit(text)
        vectors = vectorizer.transform(text).toarray()
        features = vectorizer.get_feature_names()
        return vectors, features

    def GetUniqueText(self,vectors,features):
        isUnique = False
        uniqueText = []
        for i in range(len(vectors[0])):
            isUnique = False
            for j in range(len(vectors)):
                if isUnique == False and vectors[j][i] > 0:
                    isUnique = True
                elif isUnique == True and vectors[j][i] > 0:
                    isUnique = False
                    break
            if isUnique == True:
                uniqueText.append(features[i])
        return uniqueText

    def GetSimilarity(self,text):
        vectors, features = self.GetVectorsAndFeatures(text)
        uniqueText = self.GetUniqueText(vectors, features)
        similarity = self.GetCosineSimilarity(vectors)
        similarity = np.triu(np.array(similarity)) 
        return uniqueText, similarity

    def GetSingleSimilarity(self,text):
        vectors, features = self.GetVectorsAndFeatures(text)
        similarity = self.CustomCosineSimilarity(vectors[:][0],vectors[:][1])
        return similarity

    def GetSingleUniqueText(self,text):
        vectors, features = self.GetVectorsAndFeatures(text)
        uniqueText = self.GetUniqueText(vectors, features)
        return uniqueText