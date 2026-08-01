import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, Button } from 'react-native';
import { getAIResult } from '../utils/api';

export default function AIResultScreen() {
  const [status, setStatus] = useState('PROCESSING');
  const [result, setResult] = useState(null);

  const fetchResult = async () => {
    try {
      const data = await getAIResult();
      setStatus(data.status);
      if (data.status === 'DONE') {
        setResult(data.result);
      }
    } catch (error) {
      setStatus('FAILED');
    }
  };

  useEffect(() => {
    const interval = setInterval(() => {
      if (status !== 'DONE' && status !== 'FAILED') {
        fetchResult();
      }
    }, 5000); // Poll every 5 seconds
    
    // Initial fetch
    fetchResult();

    return () => clearInterval(interval);
  }, [status]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>AI Inference Result</Text>
      
      {status === 'PROCESSING' || status === 'UPLOADED' ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color="#0000ff" />
          <Text style={{ marginTop: 10 }}>AI is processing the video...</Text>
        </View>
      ) : status === 'FAILED' ? (
        <View style={styles.center}>
          <Text style={{ color: 'red', fontSize: 18 }}>Inference Failed.</Text>
          <Button title="Retry Check" onPress={fetchResult} />
        </View>
      ) : (
        <View>
          {result && result.arac_bilgisi && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Vehicle Info</Text>
              <Text>Type: {result.arac_bilgisi.tip}</Text>
              <Text>Plate: {result.arac_bilgisi.plaka}</Text>
              <Text>Color: {result.arac_bilgisi.renk}</Text>
              <Text>Confidence: {result.arac_bilgisi.confidence_score}</Text>
            </View>
          )}

          {result && result.tespitler && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>Detections ({result.tespitler.length})</Text>
              {result.tespitler.map((item, index) => (
                <View key={index} style={styles.detectionItem}>
                  <Text style={styles.time}>{item.zaman_saniye}s</Text>
                  <Text style={styles.category}>{item.kategori}</Text>
                  <Text style={styles.label}>{item.etiket}</Text>
                  <Text style={styles.conf}>{(item.confidence_score * 100).toFixed(1)}%</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, backgroundColor: '#f5f5f5', flexGrow: 1 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20, textAlign: 'center' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 50 },
  card: { backgroundColor: '#fff', padding: 15, borderRadius: 8, marginBottom: 20, shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 5, elevation: 3 },
  cardTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 10, color: '#333' },
  detectionItem: { flexDirection: 'row', justifyContent: 'space-between', borderBottomWidth: 1, borderBottomColor: '#eee', paddingVertical: 8 },
  time: { flex: 1, fontWeight: 'bold' },
  category: { flex: 2, color: '#666' },
  label: { flex: 2, color: '#000' },
  conf: { flex: 1, textAlign: 'right' }
});
