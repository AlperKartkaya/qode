import React, { useState, useCallback, useLayoutEffect } from 'react';
import { View, Text, StyleSheet, RefreshControl, SafeAreaView, TouchableOpacity, Platform } from 'react-native';
import { KeyboardAwareScrollView } from 'react-native-keyboard-aware-scroll-view';
import { useVideoPlayer } from 'expo-video';
import * as DocumentPicker from 'expo-document-picker';
import { createQoDSession, uploadVideo, runAI } from '../utils/api';
import { showToast } from '../utils/toast';
import { Ionicons } from '@expo/vector-icons';
import SessionCard from '../components/SessionCard';
import NetworkQualityCard from '../components/NetworkQualityCard';
import VideoStreamCard from '../components/VideoStreamCard';

export default function HomeScreen({ route, navigation }) {
  const { phoneNumber } = route.params;
  const [qodStatus, setQodStatus] = useState('INACTIVE');
  const [qodLoading, setQodLoading] = useState(false);
  const [videoUri, setVideoUri] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useLayoutEffect(() => {
    navigation.setOptions({
      title: `Dashboard`,
      headerRight: () => (
        <TouchableOpacity onPress={() => navigation.replace('NumberVerify')} style={{ marginRight: 15 }}>
          <Ionicons name="log-out-outline" size={24} color="#EF4444" />
        </TouchableOpacity>
      ),
    });
  }, [navigation, phoneNumber]);

  const player = useVideoPlayer(videoUri, player => {
    player.loop = true;
    player.play();
  });

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      showToast('Dashboard data refreshed.');
    }, 1000);
  }, []);

  const handleQoD = async () => {
    if (qodStatus === 'ACTIVE' || qodStatus === 'REQUESTED') {
      // Handle deactivate
      setQodLoading(true);
      showToast('Deactivating Quality-on-Demand session...');
      setTimeout(() => {
        setQodStatus('INACTIVE');
        setQodLoading(false);
        showToast('QoD Deactivated successfully.');
      }, 1000);
      return;
    }

    // Handle activate
    setQodLoading(true);
    setQodStatus('REQUESTED');
    showToast('Requesting Quality-on-Demand session for improved bandwidth...');
    try {
      const session = await createQoDSession(60);
      if (session) {
        setQodStatus('ACTIVE');
        showToast('QoD Activated.');
      }
    } catch (error) {
      setQodStatus('INACTIVE');
      showToast('QoD Error: Failed to activate Quality on Demand.', true);
    } finally {
      setQodLoading(false);
    }
  };

  const pickVideo = async (urlStr) => {
    // Eğer bir metin (URL) geldiyse (YouTube)
    if (typeof urlStr === 'string') {
      // expo-video youtube linklerini direkt çalamaz, demo için test amaçlı sahte bir mp4 yüklüyoruz gibi gösterelim
      // ya da sadece youtube linkini videoUri'ye atayalım
      setVideoUri(urlStr);
      showToast('YouTube link selected.');
      return;
    }

    let result = await DocumentPicker.getDocumentAsync({ type: 'video/mp4' });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      setVideoUri(result.assets[0].uri);
      showToast('Video source selected successfully.');
    }
  };

  const handleUploadAndRunAI = async () => {
    if (!videoUri) return;
    setUploading(true);
    try {
      if (videoUri.includes('youtube.com') || videoUri.includes('youtu.be')) {
        // YouTube link upload simulasyonu (Backend'e gerçek dosya yerine link gönderilir, burada simüle ediyoruz)
        showToast('YouTube URL gönderiliyor...');
        await new Promise(resolve => setTimeout(resolve, 1000));
        showToast('202 Accepted -> AI tetiklenir');
      } else {
        await uploadVideo(videoUri);
        showToast('202 Accepted -> AI tetiklenir');
      }
      
      await runAI();
      navigation.navigate('AIResult');
    } catch (error) {
      showToast('Error uploading video.', true);
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAwareScrollView 
        style={{ flex: 1 }}
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4338CA']} />}
        keyboardShouldPersistTaps="handled"
        enableOnAndroid={true}
        extraHeight={225}
        extraScrollHeight={225}
      >
        <SessionCard phoneNumber={phoneNumber} />

        <NetworkQualityCard 
          status={qodStatus} 
          loading={qodLoading} 
          onActivate={handleQoD} 
        />

        <VideoStreamCard 
          videoUri={videoUri} 
          uploading={uploading} 
          player={player} 
          isQodActive={qodStatus === 'ACTIVE'}
          onSelectVideo={pickVideo} 
          onClearVideo={() => setVideoUri(null)}
          onUpload={handleUploadAndRunAI} 
        />
      </KeyboardAwareScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#F3F4F6' },
  container: { padding: 16, flexGrow: 1 },
});
