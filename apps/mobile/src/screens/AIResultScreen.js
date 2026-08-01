import React, { useState, useEffect, useCallback, useLayoutEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, TouchableOpacity, RefreshControl, SafeAreaView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { getAIResult } from '../utils/api';
import { showToast } from '../utils/toast';

export default function AIResultScreen({ navigation }) {
  const [status, setStatus] = useState('PROCESSING');
  const [result, setResult] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchResult = async (isManualRefresh = false) => {
    try {
      if (isManualRefresh) setRefreshing(true);
      const data = await getAIResult();
      setStatus(data.status);
      if (data.status === 'DONE') {
        setResult(data.result);
        if (isManualRefresh) showToast('AI results updated successfully.');
      } else if (isManualRefresh) {
        showToast('AI is still processing the video...');
      }
    } catch (error) {
      setStatus('FAILED');
      showToast('Error fetching AI results.', true);
    } finally {
      if (isManualRefresh) setRefreshing(false);
    }
  };

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <TouchableOpacity onPress={() => fetchResult(true)} style={{ marginRight: 15 }}>
          <Ionicons name="refresh-outline" size={24} color="#4338CA" />
        </TouchableOpacity>
      ),
    });
  }, [navigation]);

  const onRefresh = useCallback(() => {
    fetchResult(true);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      if (status !== 'DONE' && status !== 'FAILED') {
        fetchResult();
      }
    }, 3000);
    
    fetchResult();
    return () => clearInterval(interval);
  }, [status]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView 
        contentContainerStyle={styles.container}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4338CA']} />}
      >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Inference Result</Text>
        <Text style={styles.headerSubtitle}>Computer Vision Analysis</Text>
      </View>
      
      {status === 'PROCESSING' || status === 'UPLOADED' ? (
        <View style={styles.centerBox}>
          <ActivityIndicator size="large" color="#4338CA" />
          <Text style={styles.loadingText}>Analyzing Video Frames...</Text>
          <Text style={styles.subLoadingText}>Detecting vehicles and road risks</Text>
        </View>
      ) : status === 'FAILED' ? (
        <View style={styles.centerBox}>
          <Ionicons name="warning" size={48} color="#EF4444" />
          <Text style={styles.errorText}>Inference Failed</Text>
          <TouchableOpacity style={styles.retryButton} onPress={fetchResult}>
            <Text style={styles.retryButtonText}>Retry Fetching</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View>
          <View style={styles.successBanner}>
            <Ionicons name="checkmark-circle" size={24} color="#10B981" />
            <Text style={styles.successText}>Analysis Complete</Text>
          </View>

          {result && result.arac_bilgisi && (
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="car-sport" size={22} color="#4338CA" />
                <Text style={styles.cardTitle}>Vehicle Details</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Type</Text>
                <Text style={styles.detailValue}>{result.arac_bilgisi.tip}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Plate</Text>
                <Text style={styles.detailValue}>{result.arac_bilgisi.plaka}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Color</Text>
                <Text style={styles.detailValue}>{result.arac_bilgisi.renk}</Text>
              </View>
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Confidence</Text>
                <Text style={styles.detailValue}>{(result.arac_bilgisi.confidence_score * 100).toFixed(1)}%</Text>
              </View>
            </View>
          )}

          {result && result.tespitler && (
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="scan-circle" size={22} color="#4338CA" />
                <Text style={styles.cardTitle}>Timeline Detections</Text>
                <View style={styles.countBadge}>
                  <Text style={styles.countText}>{result.tespitler.length}</Text>
                </View>
              </View>
              
              {result.tespitler.map((item, index) => (
                <View key={index} style={styles.detectionItem}>
                  <View style={styles.timeBadge}>
                    <Text style={styles.timeText}>{item.zaman_saniye}s</Text>
                  </View>
                  <View style={styles.detectionContent}>
                    <Text style={styles.categoryText}>{item.kategori}</Text>
                    <Text style={styles.labelText}>{item.etiket}</Text>
                  </View>
                  <View style={styles.confBadge}>
                    <Text style={styles.confText}>{(item.confidence_score * 100).toFixed(0)}%</Text>
                  </View>
                </View>
              ))}
            </View>
          )}

          {/* Ham JSON Gösterimi */}
          {result && (
            <View style={styles.card}>
              <View style={styles.cardHeader}>
                <Ionicons name="code-slash" size={22} color="#4338CA" />
                <Text style={styles.cardTitle}>Ham JSON</Text>
              </View>
              <View style={styles.jsonContainer}>
                <Text style={styles.jsonText}>{JSON.stringify(result, null, 2)}</Text>
              </View>
            </View>
          )}
        </View>
      )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#F3F4F6' },
  container: { padding: 20, flexGrow: 1 },
  header: { marginBottom: 24, marginTop: 10 },
  headerTitle: { fontSize: 32, fontWeight: '800', color: '#111827' },
  headerSubtitle: { fontSize: 16, color: '#6B7280', fontWeight: '500', marginTop: 4 },
  centerBox: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 16, padding: 40, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  loadingText: { marginTop: 24, fontSize: 18, fontWeight: '700', color: '#111827' },
  subLoadingText: { marginTop: 8, fontSize: 14, color: '#6B7280', textAlign: 'center' },
  errorText: { marginTop: 16, fontSize: 20, fontWeight: '700', color: '#EF4444' },
  retryButton: { marginTop: 24, backgroundColor: '#EF4444', paddingHorizontal: 24, paddingVertical: 12, borderRadius: 8 },
  retryButtonText: { color: '#FFFFFF', fontWeight: '600' },
  successBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#DEF7EC', padding: 16, borderRadius: 12, marginBottom: 20 },
  successText: { marginLeft: 12, fontSize: 16, fontWeight: '700', color: '#03543F' },
  card: { backgroundColor: '#FFFFFF', padding: 20, borderRadius: 16, marginBottom: 20, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 10, elevation: 3 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  cardTitle: { fontSize: 18, fontWeight: '700', color: '#111827', marginLeft: 10, flex: 1 },
  countBadge: { backgroundColor: '#EEF2FF', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  countText: { color: '#4338CA', fontWeight: '700', fontSize: 12 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  detailLabel: { color: '#6B7280', fontSize: 15, fontWeight: '500' },
  detailValue: { color: '#111827', fontSize: 15, fontWeight: '700' },
  detectionItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  timeBadge: { backgroundColor: '#F3F4F6', width: 44, height: 44, borderRadius: 22, justifyContent: 'center', alignItems: 'center', marginRight: 16 },
  timeText: { fontSize: 13, fontWeight: '700', color: '#4B5563' },
  detectionContent: { flex: 1 },
  categoryText: { fontSize: 13, color: '#6B7280', marginBottom: 2 },
  labelText: { fontSize: 15, fontWeight: '600', color: '#111827' },
  confBadge: { backgroundColor: '#ECFCCB', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  confText: { fontSize: 12, fontWeight: '700', color: '#3F6212' },
  jsonContainer: { backgroundColor: '#111827', padding: 16, borderRadius: 12 },
  jsonText: { color: '#34D399', fontFamily: 'Courier', fontSize: 12 },
});
