import React, { useState } from 'react';
import { View, Text, Button, StyleSheet, ActivityIndicator, Alert, ScrollView } from 'react-native';
import { createQoDSession, uploadVideo, runAI } from '../utils/api';
import * as DocumentPicker from 'expo-document-picker';
import { Video } from 'expo-av';

export default function HomeScreen({ route, navigation }) {
  const { phoneNumber } = route.params;
  const [qodStatus, setQodStatus] = useState('INACTIVE'); // INACTIVE, REQUESTED, ACTIVE
  const [qodLoading, setQodLoading] = useState(false);
  const [videoUri, setVideoUri] = useState(null);
  const [uploading, setUploading] = useState(false);

  // In reality, this would play the HLS stream from TEKNOFEST
  // `https://teknofest-arge-turkcell.ercdn.net/hls/4/pZ/faz2/faz2.smil/playlist.m3u8`
  
  const handleQoD = async () => {
    setQodLoading(true);
    setQodStatus('REQUESTED');
    try {
      const session = await createQoDSession(60);
      if (session) {
        setQodStatus('ACTIVE');
        Alert.alert('QoD Activated', 'Quality on Demand session created successfully for 60 seconds.');
      }
    } catch (error) {
      setQodStatus('INACTIVE');
      Alert.alert('QoD Error', 'Failed to activate QoD.');
    } finally {
      setQodLoading(false);
    }
  };

  const pickVideo = async () => {
    let result = await DocumentPicker.getDocumentAsync({
      type: 'video/mp4',
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      setVideoUri(result.assets[0].uri);
    }
  };

  const handleUploadAndRunAI = async () => {
    if (!videoUri) {
      Alert.alert('No Video', 'Please select or record a video first.');
      return;
    }
    
    setUploading(true);
    try {
      await uploadVideo(videoUri);
      await runAI();
      navigation.navigate('AIResult');
    } catch (error) {
      Alert.alert('Error', 'Failed to upload video or start AI.');
      console.error(error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.cardTitle}>SESSION</Text>
        <Text>Status: ✅ Verified</Text>
        <Text>Phone: {phoneNumber}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>QOD SESSION</Text>
        <Text>Status: {qodStatus}</Text>
        {qodLoading ? (
          <ActivityIndicator size="small" color="#0000ff" />
        ) : (
          <Button title="Activate QoD (1080p Stream)" onPress={handleQoD} disabled={qodStatus === 'ACTIVE'} />
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>TEKNOFEST STREAM</Text>
        <Button title="Select Video (Simulate Stream Record)" onPress={pickVideo} />
        
        {videoUri && (
          <Video
            source={{ uri: videoUri }}
            style={styles.video}
            useNativeControls
            resizeMode="contain"
          />
        )}

        <View style={{ marginTop: 20 }}>
          {uploading ? (
            <ActivityIndicator size="large" color="#0000ff" />
          ) : (
            <Button title="Upload to Backend & Run AI" onPress={handleUploadAndRunAI} color="green" />
          )}
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#f5f5f5', flexGrow: 1 },
  card: { backgroundColor: '#fff', padding: 15, borderRadius: 8, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 5, elevation: 3 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 10, color: '#333' },
  video: { width: '100%', height: 200, backgroundColor: '#000', marginTop: 10, borderRadius: 8 },
});
