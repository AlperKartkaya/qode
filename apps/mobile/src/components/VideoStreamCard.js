import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, TextInput } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { VideoView } from 'expo-video';

export default function VideoStreamCard({ videoUri, uploading, player, isQodActive, onSelectVideo, onClearVideo, onUpload }) {
  const [sourceType, setSourceType] = useState('HLS');
  const [youtubeLink, setYoutubeLink] = useState('');
  
  const videoQuality = isQodActive ? '↑ 1080p' : '↓ 240p';
  const qualityColor = isQodActive ? '#10B981' : '#F59E0B';

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="videocam" size={20} color="#4338CA" />
        <Text style={styles.cardTitle}>TEKNOFEST KARTI</Text>
      </View>
      
      <View style={styles.infoBox}>
        <View style={styles.infoCol}>
          <Text style={styles.infoLabel}>KAYNAK SEÇ</Text>
          <View style={styles.sourceSelector}>
            <TouchableOpacity onPress={() => setSourceType('HLS')} style={[styles.sourceBtn, sourceType === 'HLS' && styles.sourceBtnActive]}>
              <Text style={[styles.sourceText, sourceType === 'HLS' && styles.sourceTextActive]}>HLS</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={() => setSourceType('YouTube')} style={[styles.sourceBtn, sourceType === 'YouTube' && styles.sourceBtnActive]}>
              <Text style={[styles.sourceText, sourceType === 'YouTube' && styles.sourceTextActive]}>YouTube</Text>
            </TouchableOpacity>
          </View>
        </View>
        <View style={[styles.infoCol, {alignItems: 'flex-end', justifyContent: 'center'}]}>
          <Text style={styles.infoLabel}>QOD {isQodActive ? 'AÇIK' : 'KAPALI'}</Text>
          <Text style={[styles.infoValue, {color: qualityColor}]}>{videoQuality}</Text>
        </View>
      </View>

      {!videoUri ? (
        <View>
          {sourceType === 'YouTube' && (
            <View style={styles.youtubeInputContainer}>
              <View style={styles.inputWrapper}>
                <TextInput
                  style={styles.youtubeInput}
                  placeholder="YouTube URL'sini buraya yapıştırın"
                  placeholderTextColor="#9CA3AF"
                  value={youtubeLink}
                  onChangeText={setYoutubeLink}
                />
                {youtubeLink.length > 0 && (
                  <TouchableOpacity style={styles.youtubeClearIcon} onPress={() => setYoutubeLink('')}>
                    <Ionicons name="close-circle" size={24} color="#6B7280" />
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}
          
          <TouchableOpacity 
            style={styles.secondaryButton} 
            onPress={sourceType === 'YouTube' && youtubeLink ? () => onSelectVideo(youtubeLink) : onSelectVideo}
          >
            <Ionicons name={sourceType === 'YouTube' ? "logo-youtube" : "play-circle-outline"} size={22} color="#4338CA" style={styles.buttonIcon} />
            <Text style={styles.secondaryButtonText}>
              {sourceType === 'YouTube' ? 'YouTube Start' : 'Teknofest Start'}
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View>
          <View style={styles.videoContainer}>
            <VideoView
              style={styles.video}
              player={player}
              allowsFullscreen
              allowsPictureInPicture
              contentFit="contain"
            />
            {!uploading && (
              <TouchableOpacity style={styles.clearButton} onPress={onClearVideo}>
                <Ionicons name="close" size={24} color="#FFFFFF" />
              </TouchableOpacity>
            )}
          </View>
          
          <TouchableOpacity 
            style={[styles.primaryButton, uploading && styles.buttonDisabled, { marginTop: 16 }]} 
            onPress={onUpload}
            disabled={uploading}
          >
            {uploading ? (
              <ActivityIndicator size="small" color="#FFFFFF" />
            ) : (
              <View style={styles.buttonContent}>
                <Ionicons name="cloud-upload-outline" size={22} color="#FFFFFF" style={styles.buttonIcon} />
                <Text style={styles.buttonText}>Upload Video to Backend</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', padding: 20, borderRadius: 12, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: '700', color: '#6B7280', marginLeft: 8, letterSpacing: 1 },
  infoBox: { flexDirection: 'row', justifyContent: 'space-between', backgroundColor: '#F9FAFB', padding: 12, borderRadius: 8, marginBottom: 16 },
  infoCol: { flex: 1 },
  infoLabel: { fontSize: 11, fontWeight: '700', color: '#9CA3AF', marginBottom: 8 },
  infoValue: { fontSize: 14, fontWeight: '700', color: '#111827' },
  sourceSelector: { flexDirection: 'row', backgroundColor: '#E5E7EB', borderRadius: 6, padding: 4, alignSelf: 'flex-start' },
  sourceBtn: { paddingVertical: 6, paddingHorizontal: 12, borderRadius: 4 },
  sourceBtnActive: { backgroundColor: '#FFFFFF', shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 1, elevation: 1 },
  sourceText: { fontSize: 13, fontWeight: '600', color: '#6B7280' },
  sourceTextActive: { color: '#4338CA' },
  youtubeInputContainer: { marginBottom: 12 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#F9FAFB', borderWidth: 1, borderColor: '#E5E7EB', borderRadius: 8, height: 56 },
  youtubeInput: { flex: 1, paddingHorizontal: 16, fontSize: 15, color: '#111827', height: '100%' },
  youtubeClearIcon: { padding: 12, justifyContent: 'center', alignItems: 'center' },
  secondaryButton: { backgroundColor: '#EEF2FF', height: 56, borderRadius: 12, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: '#C7D2FE' },
  secondaryButtonText: { color: '#4338CA', fontSize: 16, fontWeight: '600' },
  primaryButton: { backgroundColor: '#10B981', height: 56, borderRadius: 12, justifyContent: 'center', alignItems: 'center', shadowColor: '#10B981', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.2, shadowRadius: 8, elevation: 4 },
  buttonDisabled: { opacity: 0.6 },
  buttonContent: { flexDirection: 'row', alignItems: 'center' },
  buttonIcon: { marginRight: 8 },
  buttonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '600' },
  videoContainer: { borderRadius: 8, overflow: 'hidden', backgroundColor: 'transparent', width: '100%', aspectRatio: 16 / 9, position: 'relative' },
  video: { width: '100%', height: '100%' },
  clearButton: { position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(0,0,0,0.6)', width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
});
