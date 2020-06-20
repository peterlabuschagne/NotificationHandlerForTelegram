import numpy as np
import time

from collections import Counter
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

    def getSingleSimilarity(self,text):
        vectors, _ = self.GetVectorsAndFeatures(text)
        similarity = self.CustomCosineSimilarity(vectors[:][0],vectors[:][1])
        return similarity

    def GetSingleUniqueText(self,text):
        vectors, features = self.GetVectorsAndFeatures(text)
        uniqueText = self.GetUniqueText(vectors, features)
        return uniqueText

    def CompareMessages(self,messageDict,similarityDict):
        if self.isEmpty(similarityDict): # if this is the first comparison being made
            text, keys = self.getFirstComparisonTextAndKeys(messageDict)
            similarity = self.getSingleSimilarity(text)
            if similarity > 0.7:
                similarityDict[keys[0]] = [keys[1]]
            else:
                similarityDict[keys[0]] = []
                similarityDict[keys[1]] = []
        else:
            parent, child = self.existingComparisons(similarityDict)
            tempParent, tempKey = self.messagesToCompare(messageDict,parent,child)
            similarityDict = self.addToSimilarityDict(tempParent,tempKey,similarityDict)
        return similarityDict

    def isEmpty(self,anyStructure):
        if anyStructure:
            return False
        else:
            return True

    def getFirstComparisonTextAndKeys(self,messageDict):
        text = []
        keys = [list(messageDict.keys())[0]]
        keys.append(list(messageDict.keys())[1])
        text.append(messageDict[keys[0]])
        text.append(messageDict[keys[1]])
        return text, keys

    def existingComparisons(self,similarityDict):
        parent = [p for p in similarityDict.keys()]
        child = self.getChild(similarityDict)
        return parent, child    

    def getChild(self,similarityDict):
        values = [v for v in similarityDict.values()]
        child = []
        for sublist in values:
            for item in sublist:
                child.append(item)
        return child

    def messagesToCompare(self,messageDict,parent,child):
        text = []
        keys = []
        i = 0
        for key in messageDict.keys():
            if key not in parent: # if key is in parent, then don't need to compare it to itself
                if key not in child: # compare to see if similar to any parents
                    for p in parent:
                        text.clear()
                        text.append(messageDict[p]) 
                        text.append(messageDict[key])
                        similarity = self.getSingleSimilarity(text)
                        if similarity > 0.7:
                            keys.append(p)
                            keys.append(key)
                            return False, keys
                        tempParent = key
                        i += 1
        return tempParent, False

    def addToSimilarityDict(self,tempParent,tempKey,similarityDict):
        tempDict = dict()
        tempDict = similarityDict
        if not tempParent: # == False
            tempDict[tempKey[0]] = [tempKey[1]] + tempDict[tempKey[0]]
        if not tempKey: # == False
            tempDict[tempParent] = []
        return tempDict