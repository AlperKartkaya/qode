import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

export default function NetworkQualityCard({ status, loading, onActivate }) {
  const isRequested = status === 'REQUESTED' || status === 'ACTIVE';
  
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Ionicons name="cellular" size={20} color="#4338CA" />
        <Text style={styles.cardTitle}>QOD SESSİON</Text>
      </View>
      
      <View style={styles.statusRow}>
        <Text style={styles.statusLabel}>qosStatus:</Text>
        <View style={[styles.badge, isRequested ? styles.badgeActive : styles.badgeInactive]}>
          <Text style={[styles.badgeText, isRequested ? styles.badgeTextActive : styles.badgeTextInactive]}>
            {status}
          </Text>
        </View>
      </View>

      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>Trafik Hedefi</Text>
        <Text style={styles.detailValue}>0.0.0.0/0 (Tüm Cihaz)</Text>
      </View>

      {isRequested && (
        <View style={styles.detailRow}>
          <Text style={styles.detailLabel}>Süre</Text>
          <Text style={styles.detailValue}>60 Saniye</Text>
        </View>
      )}
      
      <View style={styles.detailRow}>
        <Text style={styles.detailLabel}>Profil</Text>
        <Text style={styles.detailValue}>teknofest2026</Text>
      </View>
      
      {!isRequested ? (
        <TouchableOpacity 
          style={[styles.button, {marginTop: 16}]} 
          onPress={onActivate} 
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : (
            <View style={styles.buttonContent}>
              <Ionicons name="speedometer-outline" size={20} color="#FFFFFF" style={styles.buttonIcon} />
              <Text style={styles.buttonText}>QoD Başlat</Text>
            </View>
          )}
        </TouchableOpacity>
      ) : (
        <TouchableOpacity 
          style={[styles.buttonDeactivate, {marginTop: 16}]} 
          onPress={onActivate} 
          disabled={loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#EF4444" />
          ) : (
            <View style={styles.buttonContent}>
              <Ionicons name="close-circle-outline" size={20} color="#EF4444" style={styles.buttonIcon} />
              <Text style={styles.buttonTextDeactivate}>QoD İptal Et</Text>
            </View>
          )}
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', padding: 20, borderRadius: 12, marginBottom: 16, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: '700', color: '#6B7280', marginLeft: 8, letterSpacing: 1 },
  statusRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  statusLabel: { fontSize: 14, color: '#4B5563', fontWeight: '500' },
  badge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  badgeInactive: { backgroundColor: '#F3F4F6' },
  badgeActive: { backgroundColor: '#DBEAFE' },
  badgeText: { fontSize: 13, fontWeight: '700' },
  badgeTextInactive: { color: '#6B7280' },
  badgeTextActive: { color: '#1D4ED8' }, // Blue color for REQUESTED/ACTIVE
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  detailLabel: { color: '#6B7280', fontSize: 14, fontWeight: '500' },
  detailValue: { color: '#111827', fontSize: 14, fontWeight: '600' },
  button: { backgroundColor: '#4338CA', height: 48, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  buttonDisabled: { opacity: 0.6 },
  buttonDeactivate: { backgroundColor: '#FEF2F2', height: 48, borderRadius: 10, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: '#FECACA' },
  buttonContent: { flexDirection: 'row', alignItems: 'center' },
  buttonIcon: { marginRight: 8 },
  buttonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '600' },
  buttonTextDeactivate: { color: '#EF4444', fontSize: 15, fontWeight: '600' },
});
